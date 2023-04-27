use serenity::model::prelude::interaction::application_command::ApplicationCommandInteraction;
use serenity::prelude::*;
use serenity::{builder::CreateApplicationCommand, model::Permissions};

use crate::handler::snowflake_as_db;
use crate::DatabasePoolHolder;

use tracing::*;

use super::CommandResponse;

pub fn register(command: &mut CreateApplicationCommand) -> &mut CreateApplicationCommand {
    command
        .name("setup")
        .description("Initialize bot for use in this server")
        .default_member_permissions(Permissions::ADMINISTRATOR)
        .dm_permission(false)
}

pub async fn run(
    ctx: &Context,
    command: &ApplicationCommandInteraction,
) -> Result<Option<CommandResponse>, String> {
    let type_map = ctx.data.read().await;
    let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
    let pool = pool_holder.as_ref();

    let channel_id = snowflake_as_db(command.channel_id);
    let guild_id = snowflake_as_db(
        command
            .guild_id
            .expect("Received guild-only interaction without guild provided?!"),
    );

    if let Err(why) = sqlx::query!(
        "INSERT INTO guild_rule (guild_id, system_message_channel_id, kick_safety_timeout, pending_kick_notification_values) VALUES (?, ?, ?, ?)",
        guild_id, channel_id, 600,
        "3600 7200 21600 43200 86400 259200 604800 1209600"
    ).execute(pool).await {
        error!("Error while making initial guild rule for {guild_id}: {why}");
        return Err(format!("Error while making initial guild rule: {why}"));
    }

    Ok(CommandResponse::text("Created basic rule for this server, using this channel for system messages. Use `/rule` to view and edit it.".to_owned()))
}
