use serenity::{
    builder::CreateApplicationCommand,
    model::{
        prelude::{
            interaction::application_command::{
                ApplicationCommandInteraction, CommandDataOptionValue,
            },
            ChannelType,
        },
        Permissions,
    },
    prelude::Context,
};

use crate::{handler::snowflake_as_db, DatabasePoolHolder};

use super::CommandResponse;

pub fn system_register(command: &mut CreateApplicationCommand) -> &mut CreateApplicationCommand {
    command
        .name("syschannel")
        .description("Set channel for system messages from this bot")
        .default_member_permissions(Permissions::ADMINISTRATOR)
        .dm_permission(false)
        .set_options(vec![])
        .create_option(|opt| {
            opt.name("syschannelid")
                .description("Which channel to set")
                .kind(serenity::model::prelude::command::CommandOptionType::Channel)
                .required(true)
        })
}

pub fn notify_register(command: &mut CreateApplicationCommand) -> &mut CreateApplicationCommand {
    command
        .name("pendingchannel")
        .description("Set channel for notifications that a kick is pending")
        .default_member_permissions(Permissions::ADMINISTRATOR)
        .dm_permission(false)
        .set_options(vec![])
        .create_option(|opt| {
            opt.name("pendingchannelid")
                .description("Which channel to set (empty to unset)")
                .kind(serenity::model::prelude::command::CommandOptionType::Channel)
                .required(false)
        })
}

pub async fn system_run(
    ctx: &Context,
    command: &ApplicationCommandInteraction,
) -> Result<Option<CommandResponse>, String> {
    let type_map = ctx.data.read().await;
    let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
    let pool = pool_holder.as_ref();

    // Retreive the new channel argument
    let new_channel_id;
    let new_channel;
    let option = match command.data.options.get(0) {
        None => return Err("Expected argument to command but got none".to_string()),
        Some(opt) => match opt.resolved.as_ref() {
            Some(v) => v,
            None => return Err("Expected resolvable argument to command but got none".to_string()),
        },
    };
    if let CommandDataOptionValue::Channel(channel) = option {
        new_channel_id = snowflake_as_db(channel.id);
        new_channel = channel;
    } else {
        return Err(format!("Expected to receive channel, but got: {option:?}"));
    }

    // Check that there is already a rule for this guild.
    let guild_id = snowflake_as_db(
        command
            .guild_id
            .expect("Received guild-only interaction without guild provided?!"),
    );

    let _rule = match sqlx::query!("SELECT * FROM guild_rule WHERE guild_id = ?", guild_id)
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

    // Ensure that the new channel is a text channel
    if new_channel.kind != ChannelType::Text {
        return Err(format!(
            "The provided channel is not a text channel, but a {:?}",
            new_channel.kind
        ));
    }

    // Try sending a message to the new channel.
    if let Err(why) = new_channel
        .id
        .say(&ctx.http, "This will be the new system message channel.")
        .await
    {
        return Err(format!(
            "Could not send message to new system message channel: {why}"
        ));
    }

    match sqlx::query!(
        "UPDATE guild_rule SET system_message_channel_id=? WHERE guild_id = ?",
        new_channel_id,
        guild_id
    )
    .execute(pool)
    .await
    {
        Ok(rule) => rule,
        Err(why) => return Err(format!("Error while setting system message channel: {why}")),
    };

    Ok(CommandResponse::ephemeral_text(format!(
        "Successfully set system message channel to <#{}>!",
        new_channel_id
    )))
}

pub async fn notify_run(
    ctx: &Context,
    command: &ApplicationCommandInteraction,
) -> Result<Option<CommandResponse>, String> {
    let type_map = ctx.data.read().await;
    let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
    let pool = pool_holder.as_ref();

    // Check that there is already a rule for this guild.
    let guild_id = snowflake_as_db(
        command
            .guild_id
            .expect("Received guild-only interaction without guild provided?!"),
    );

    let _rule = match sqlx::query!("SELECT * FROM guild_rule WHERE guild_id = ?", guild_id)
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

    // Retreive the new channel argument. If not provided, escape to unset
    let new_channel_id;
    let new_channel;
    let option = match command.data.options.get(0) {
        None => return notify_channel_unset(ctx, guild_id).await,
        Some(opt) => match opt.resolved.as_ref() {
            Some(v) => v,
            None => return notify_channel_unset(ctx, guild_id).await,
        },
    };
    if let CommandDataOptionValue::Channel(channel) = option {
        new_channel_id = snowflake_as_db(channel.id);
        new_channel = channel;
    } else {
        return Err(format!("Expected to receive channel, but got: {option:?}"));
    }

    // Ensure that the new channel is a text channel
    if new_channel.kind != ChannelType::Text {
        return Err(format!(
            "The provided channel is not a text channel, but a {:?}",
            new_channel.kind
        ));
    }

    // Try sending a message to the new channel.
    if let Err(why) = new_channel
        .id
        .say(
            &ctx.http,
            "This will be the new pending notification channel.",
        )
        .await
    {
        return Err(format!(
            "Could not send message to new pending notification channel: {why}"
        ));
    }

    match sqlx::query!(
        "UPDATE guild_rule SET pending_kick_notification_channel_id=? WHERE guild_id = ?",
        new_channel_id,
        guild_id
    )
    .execute(pool)
    .await
    {
        Ok(rule) => rule,
        Err(why) => {
            return Err(format!(
                "Error while setting pending notification channel: {why}"
            ))
        }
    };

    Ok(CommandResponse::ephemeral_text(format!(
        "Successfully set pending notification channel to <#{}>!",
        new_channel_id
    )))
}

async fn notify_channel_unset(
    ctx: &Context,
    guild_id: i64,
) -> Result<Option<CommandResponse>, String> {
    let type_map = ctx.data.read().await;
    let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
    let pool = pool_holder.as_ref();

    match sqlx::query!(
        "UPDATE guild_rule SET pending_kick_notification_channel_id=NULL WHERE guild_id = ?",
        guild_id
    )
    .execute(pool)
    .await
    {
        Ok(rule) => rule,
        Err(why) => {
            return Err(format!(
                "Error while unsetting pending notification channel: {why}"
            ))
        }
    };

    Ok(CommandResponse::ephemeral_text(format!(
        "Successfully removed pending notification channel!",
    )))
}
