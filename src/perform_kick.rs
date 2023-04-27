use std::time::{Duration, SystemTime};

use serenity::collector::{EventCollectorBuilder, MessageCollectorBuilder};
use serenity::{
    collector::ReactionAction,
    json::{json, Value},
    model::prelude::{Channel, GuildChannel, Member},
    prelude::Context,
};

use crate::DatabasePoolHolder;

pub async fn run_kick(context: Context, kick_id: i64) -> anyhow::Result<()> {
    let ctx = &context;
    let type_map = ctx.data.read().await;
    let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
    let pool = pool_holder.as_ref();

    // Retrieve the kick by ID, and its associated guild's rules.
    let kick = sqlx::query!("SELECT * FROM pending_kicks WHERE id=?", kick_id)
        .fetch_one(pool)
        .await?;
    let guild_rule = sqlx::query!("SELECT * FROM guild_rule WHERE guild_id=?", kick.guild_id)
        .fetch_one(pool)
        .await?;

    let system_channel = ctx.http.get_channel(guild_rule.system_message_channel_id as u64).await?;

    // Check if the member has the immunity role. If they do, do not start the kick.
    let member_to_kick = ctx.http.get_member(kick.guild_id as u64, kick.user_id as u64).await;
    let member_to_kick = match member_to_kick {
        Ok(member) => member,
        Err(why) => {
            todo!();
        }
    };


    let make_message = |remaining: Duration, completion_fraction: f64| -> String {
        if completion_fraction >= 1.0f64 {
            format!(
                "Member <@{}> (id: {}) successfully kicked.",
                kick.user_id, kick.user_id
            )
        } else {
            let mut progress_string = String::new();
            let count = 10;
            for i in 0..count {
                let new_symb = if completion_fraction >= (i as f64 / count as f64) {
                    '◻' // WHITE MEDIUM SQUARE
                } else {
                    '⚠' // WARNING SIGN
                };
                progress_string.push(new_symb);
            }

            format!("We are about to kick <@{}> (id: {}) in {} seconds ({}).\nTo cancel, react with any emoji to this message.\n{}",
            kick.user_id, kick.user_id, remaining.as_secs(), humantime::format_duration(remaining), progress_string)
        }
    };

    // Send the first message to the guild's system message channel.
    let mut message = ctx.http.send_message(guild_rule.system_message_channel_id as u64,
        &json!({
            "content": make_message(Duration::from_secs(guild_rule.kick_safety_timeout as u64), 0.0f64)
        })).await?;

    let kick_started = SystemTime::now();
    let kick_after = SystemTime::now() + Duration::from_secs(guild_rule.kick_safety_timeout as u64);
    let kick_safety_timeout = Duration::from_secs(guild_rule.kick_safety_timeout as u64);

    // Enter a loop where we wait for reactions, and update the message.
    while kick_after.elapsed().is_err() {
        // elapsed() returns Err if the SystemTime is in the future
        let elapsed_seconds = kick_started.elapsed().unwrap_or_default().as_secs();
        let total_seconds = kick_safety_timeout.as_secs();
        let remaining_seconds = total_seconds - elapsed_seconds;
        let completion_fraction = (elapsed_seconds as f64) / (total_seconds as f64);

        message
            .edit(ctx, |m| {
                m.content(make_message(
                    Duration::from_secs(remaining_seconds),
                    completion_fraction,
                ))
            })
            .await?;

        if let Some(reaction) = message
            .await_reaction(&ctx)
            .timeout(Duration::from_secs(15))
            .await
        {
            if let ReactionAction::Added(reaction) = reaction.as_ref() {
                if let Some(member) = reaction.member.clone() {
                    // Try getting permissions of the member
                    let full_member = ctx.http.get_member(member.guild_id.expect("Received member without guild ID on guild channel message reaction?!").0, member.user.expect("Did not receive user ID on reaction?!").id.0).await?;
                    let permissions = full_member
                        .permissions(ctx)
                        .expect("Could not acquire permission bits from full member+cache");
                    if !permissions.kick_members() {
                        ctx.http.send_message(guild_rule.system_message_channel_id as u64,
                            &json!({
                                "content": format!("Sorry <@{}>, you cannot cancel a member kick because you do not have the \"Kick Members\" permission.", full_member.user.id.0),
                            })).await?;
                        continue;
                    }
                    // If here, member has permission to kick, and thus to stop the kick
                    ctx.http.send_message(guild_rule.system_message_channel_id as u64,
                        &json!({
                            "content": format!("<@{}> has stopped the pending kick of <@{}>.", full_member.user.id.0, kick.user_id),
                        })).await?;
                    sqlx::query!("DELETE FROM pending_kicks WHERE id=?", kick_id).execute(pool).await;
                    return Ok(());
                }
            }
        }
    }

    // If here, the safety timeout elapsed without the kick being stopped by a reaction.
    // We will now perform the kick.




    Ok(())
}
