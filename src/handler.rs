use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use serenity::async_trait;
use serenity::model::channel::Message;
use serenity::model::gateway::Ready;
use serenity::model::prelude::interaction::Interaction;
use serenity::model::prelude::{ChannelId, Guild, GuildId, Member, UserId};
use serenity::prelude::*;
use sqlx::SqlitePool;

use crate::kick_manager::KickManager;
use crate::{commands, DatabasePoolHolder};

use tracing::*;

pub struct Handler {
    pub is_loop_running: AtomicBool,
    pub kick_manager: Arc<Mutex<KickManager>>,
}

pub fn snowflake_as_db<T>(flake: T) -> i64
where
    T: Into<u64>,
{
    let unsigned: u64 = flake.into();
    unsigned
        .try_into()
        .expect("Program used too far in future: snowflake does not fit into i64!")
}

#[async_trait]
impl EventHandler for Handler {
    async fn ready(&self, ctx: Context, ready: Ready) {
        println!("{} is connected!", ready.user.name);

        let type_map = ctx.data.read().await;
        let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
        let pool = pool_holder.as_ref();

        // Make sure that every guild I'm in has a corresponding rule
        for guild in ready.guilds {
            let id = snowflake_as_db(guild.id);
            let rule = sqlx::query!("SELECT * FROM guild_rule WHERE guild_rule.guild_id=?;", id)
                .fetch_one(pool)
                .await;
            if let Err(_) = rule {
                // No rule for this guild.
                info!("No rule present for guild {}", guild.id);
                self.greet_new_guild(&ctx, guild.id).await;
            }
        }

        // Create global slash commands
        commands::setup_commands(&ctx).await;
    }

    async fn cache_ready(&self, ctx: Context, _guilds: Vec<GuildId>) {
        println!("Cache built successfully!");

        if !self.is_loop_running.load(Ordering::Relaxed) {
            let kick_manager = self.kick_manager.clone();
            kick_manager.lock().await.provide_context(ctx.clone());
            tokio::spawn(async move {
                loop {
                    Self::check_pending_kicks(&ctx, kick_manager.clone()).await;
                    tokio::time::sleep(Duration::from_secs(30)).await;
                }
            });
            self.is_loop_running.store(true, Ordering::Relaxed);
        }
    }

    async fn interaction_create(&self, ctx: Context, interaction: Interaction) {
        if let Interaction::ApplicationCommand(command) = interaction {
            info!("Received command interaction: {:#?}", command);
            commands::dispatch(ctx, command).await;
        }
    }

    async fn guild_create(&self, ctx: Context, guild: Guild, is_new: bool) {
        info!("Received new guild {} with is_new {is_new}", guild.id);
        if is_new {
            // Guild has just been joined
            self.greet_new_guild(&ctx, guild.id).await;
        }
    }

    async fn message(&self, ctx: Context, msg: Message) {
        if msg.content == "!count" {
            let type_map = ctx.data.read().await;
            let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
            let pool = pool_holder.as_ref();
            let data = sqlx::query!("SELECT count(1) AS c FROM pending_kicks;")
                .fetch_one(pool)
                .await;

            if let Err(why) = msg.channel_id.say(&ctx.http, format!("{data:?}")).await {
                error!("Error sending message: {why:?}");
            }
        }
    }

    async fn guild_member_addition(&self, ctx: Context, member: Member) {
        // When the member joins, add a record for it to be kicked, according to the rules in place for that guild.
        let type_map = ctx.data.read().await;
        let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
        let pool = pool_holder.as_ref();
        let id = snowflake_as_db(member.guild_id);
        let rule = sqlx::query!("SELECT * FROM guild_rule WHERE guild_rule.guild_id=?;", id)
            .fetch_one(pool)
            .await;
        if let Err(why) = rule {
            error!("Error fetching guild rule for {id}: {why}");
            return;
        }
        let rule = rule.unwrap();
        let sys_channel = ChannelId(rule.system_message_channel_id as u64);

        if let Some(timeout) = rule.new_member_kick_timeout {
            let current_time = (std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("Program run before UNIX epoch?!"))
            .as_secs() as i64;
            let res = self
                .add_pending_kick(
                    pool,
                    member.user.id,
                    member.guild_id,
                    current_time + timeout,
                    rule.immunity_role_id,
                )
                .await;
            if let Err(why) = res {
                error!("Error recording pending kick: {why}");
                if let Err(why2) = sys_channel.say(&ctx.http, format!("Error while adding pending kick for <@{}>: {why}\nPlease add a pending kick manually!", member.user.id)).await {
                    error!("Also error sending message about it: {why2}");
                }
            } else {
                if let Err(why) = sys_channel
                    .say(
                        &ctx.http,
                        format!("Successfully added pending kick for <@{}>!", member.user.id),
                    )
                    .await
                {
                    error!("Error sending message about adding pending kick: {why}");
                }
            }
        }
    }
}

impl Handler {
    async fn add_pending_kick(
        &self,
        pool: &SqlitePool,
        user_id: UserId,
        guild_id: GuildId,
        when_unix_time: i64,
        unless_has_role_id: Option<i64>,
    ) -> Result<(), sqlx::Error> {
        info!("Adding pending kick for user {user_id} in {guild_id}");
        let user_id = snowflake_as_db(user_id);
        let guild_id = snowflake_as_db(guild_id);
        sqlx::query!("INSERT INTO pending_kicks (user_id, guild_id, kick_after_unix_time, unless_has_role_id) VALUES (?, ?, ?, ?);",
        user_id,
            guild_id,
            when_unix_time,
            unless_has_role_id,
    ).execute(pool).await?;
        Ok(())
    }

    async fn greet_new_guild(&self, ctx: &Context, guild_id: GuildId) {
        // Find a channel to write to.
        // Currently limited to using the system message channel (need anything more?)

        info!("Greeting guild {guild_id}");

        let guild = Guild::get(&ctx, guild_id).await;
        if let Err(why) = guild {
            error!("Error while getting guild to greet: {why}");
            return;
        }

        let guild = guild.unwrap();
        let channel = guild.system_channel_id;
        if channel.is_none() {
            error!("Guild {guild:?} doesn't have a defined system channel!");
            return;
        }

        if let Err(why) = channel
            .unwrap()
            .say(
                &ctx.http,
                "Please configure this bot by running `/setup` from an administrator channel.",
            )
            .await
        {
            error!("Error while sending greeting message to guild {guild:?}: {why}");
            return;
        }
    }

    async fn check_pending_kicks(ctx: &Context, kick_manager: Arc<Mutex<KickManager>>) {
        let type_map = ctx.data.read().await;
        let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
        let pool = pool_holder.as_ref();

        debug!("Performing check for pending kicks...");
        let now_unix_time = std::time::UNIX_EPOCH
            .elapsed()
            .expect("Program run before UNIX epoch?!")
            .as_secs() as i64;
        match sqlx::query!(
            "SELECT * FROM pending_kicks WHERE kick_after_unix_time>?",
            now_unix_time
        )
        .fetch_all(pool)
        .await
        {
            Err(why) => error!("Error while fetching pending kicks: {why}"),
            Ok(data) => {
                let mut kick_manager = kick_manager.lock().await;
                for item in data {
                    kick_manager.provide_context(ctx.clone());
                    kick_manager.submit_kick(item.id).await;
                }
            }
        }
    }
}
