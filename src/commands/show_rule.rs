use std::time::Duration;

use serenity::model::prelude::interaction::application_command::ApplicationCommandInteraction;
use serenity::prelude::*;
use serenity::{builder::CreateApplicationCommand, model::Permissions};

use crate::handler::snowflake_as_db;
use crate::DatabasePoolHolder;

use super::CommandResponse;

pub fn register(command: &mut CreateApplicationCommand) -> &mut CreateApplicationCommand {
    command
        .name("rule")
        .description("Show currently active rule in the server")
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

    let guild_id = snowflake_as_db(
        command
            .guild_id
            .expect("Received guild-only interaction without guild provided?!"),
    );

    let rule = match sqlx::query!("SELECT * FROM guild_rule WHERE guild_id = ?", guild_id)
        .fetch_one(pool)
        .await
    {
        Ok(rule) => rule,
        Err(why) => {
            return Err(format!(
                "Error while getting current active rule (did you `/setup`?): {why}"
            ))
        }
    };

    let mut text = vec![];
    text.push(format!("Current rule:"));
    text.push(format!(
        "System message channel: <#{}> `/syschannel`",
        rule.system_message_channel_id
    ));
    if let Some(c) = rule.pending_kick_notification_channel_id {
        text.push(format!(
            "Will remind about pending kicks in: <#{}> `/pendingchannel`",
            c
        ));
    } else {
        text.push(format!(
            "Will remind about pending kicks in: unset `/pendingchannel`"
        ));
    }
    text.push(format!(
        "Reminders will be sent at seconds before kick: {:?} `/pendingreminders`",
        rule.pending_kick_notification_values
    ));

    if let Some(t) = rule.new_member_kick_timeout {
        let dur = Duration::from_secs(t as u64);
        text.push(format!(
            "New members get kicked after: {} seconds = {} `/newtimeout`",
            t,
            humantime::format_duration(dur)
        ));
    } else {
        text.push(format!("New members get kicked after: never `/newtimeout`"));
    }

    if let Some(r) = rule.immunity_role_id {
        text.push(format!("Kick immunity role: <@&{}> `/immunityrole`", r));
    } else {
        text.push(format!("Kick immunity role: unset `/immunityrole`"))
    }

    if let Some(t) = rule.loss_of_immunity_role_timeout {
        let dur = Duration::from_secs(t as u64);
        text.push(format!(
            "Members losing immunity role get kicked after: {} seconds = {} `/immunitytimeout`",
            t,
            humantime::format_duration(dur)
        ));
    } else {
        text.push(format!(
            "Members losing immunity role get kicked after: never `/immunitytimeout`"
        ));
    }

    let dur = Duration::from_secs(rule.kick_safety_timeout as u64);
    text.push(format!(
        "When kicking a member, allow cancelling within: {} seconds = {} `/safetytimeout`",
        rule.kick_safety_timeout,
        humantime::format_duration(dur)
    ));

    Ok(CommandResponse::text(text.join("\n")))
}
