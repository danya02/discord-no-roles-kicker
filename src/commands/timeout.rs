use serenity::model::prelude::interaction::application_command::{
    ApplicationCommandInteraction, CommandDataOptionValue,
};
use serenity::prelude::*;
use serenity::{builder::CreateApplicationCommand, model::Permissions};

use crate::handler::snowflake_as_db;
use crate::DatabasePoolHolder;

use super::CommandResponse;

pub fn new_register(command: &mut CreateApplicationCommand) -> &mut CreateApplicationCommand {
    command
        .name("newtimeout")
        .description("Set timeout for new members to get kicked")
        .default_member_permissions(Permissions::ADMINISTRATOR)
        .dm_permission(false)
        .create_option(|opt| {
            opt.name("newtimeoutsecs")
                .description("Seconds before a new member is kicked (empty to unset)")
                .required(false)
                .kind(serenity::model::prelude::command::CommandOptionType::Integer)
                .min_int_value(0)
                // Choices make it mandatory to choose one of a list, which we don't want
                // .add_int_choice("1 day", 86400)
                // .add_int_choice("7 days", 86400 * 7)
                // .add_int_choice("14 days", 86400 * 14)
                // .add_int_choice("31 days", 31 * 86400)
        })
}

pub fn immunity_register(command: &mut CreateApplicationCommand) -> &mut CreateApplicationCommand {
    command
        .name("immunitytimeout")
        .description("Set timeout for members losing immunity role to get kicked")
        .default_member_permissions(Permissions::ADMINISTRATOR)
        .dm_permission(false)
        .create_option(|opt| {
            opt.name("immunitytimeoutsecs")
                .description("Seconds before the member losing immunity is kicked (empty to unset)")
                .required(false)
                .kind(serenity::model::prelude::command::CommandOptionType::Integer)
                .min_int_value(0)
                // Choices make it mandatory to choose one of a list, which we don't want
                // .add_int_choice("1 day", 86400)
                // .add_int_choice("7 days", 86400 * 7)
                // .add_int_choice("14 days", 86400 * 14)
                // .add_int_choice("31 days", 31 * 86400)
        })
}

pub fn safety_register(command: &mut CreateApplicationCommand) -> &mut CreateApplicationCommand {
    command
        .name("safetytimeout")
        .description("Set time during which an administrator can stop a kick in progress")
        .default_member_permissions(Permissions::ADMINISTRATOR)
        .dm_permission(false)
        .create_option(|opt| {
            opt.name("safetytimeoutsecs")
                .description("Seconds before the member is really kicked")
                .required(true)
                .kind(serenity::model::prelude::command::CommandOptionType::Integer)
                .min_int_value(30)
                // Choices make it mandatory to choose one of a list, which we don't want
                // .add_int_choice("2 minutes", 2 * 60)
                // .add_int_choice("10 minutes", 10 * 60)
                // .add_int_choice("30 minutes", 30 * 60)
                // .add_int_choice("1 hour", 60 * 60)
        })
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TimeoutType {
    NewMember,
    ImmunityRoleLoss,
    Safety,
}

pub async fn run(
    ctx: &Context,
    command: &ApplicationCommandInteraction,
    timeout_type: TimeoutType,
) -> Result<Option<CommandResponse>, String> {
    let type_map = ctx.data.read().await;
    let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
    let pool = pool_holder.as_ref();

    let guild_id = snowflake_as_db(
        command
            .guild_id
            .expect("Received guild-only interaction without guild provided?!"),
    );

    // Retreive the new timeout argument. If none, short-circuit to unset
    let new_timeout;
    let option = match command.data.options.get(0) {
        None => return unset(ctx, guild_id, timeout_type).await,
        Some(opt) => match opt.resolved.as_ref() {
            Some(v) => v,
            None => return unset(ctx, guild_id, timeout_type).await,
        },
    };
    if let CommandDataOptionValue::Integer(timeout) = option {
        new_timeout = timeout;
    } else {
        return Err(format!("Expected to receive integer, but got: {option:?}"));
    }

    let query = match timeout_type {
        TimeoutType::NewMember => sqlx::query!(
            "UPDATE guild_rule SET new_member_kick_timeout=? WHERE guild_id=?",
            new_timeout,
            guild_id
        ),
        TimeoutType::ImmunityRoleLoss => sqlx::query!(
            "UPDATE guild_rule SET loss_of_immunity_role_timeout=? WHERE guild_id=?",
            new_timeout,
            guild_id
        ),
        TimeoutType::Safety => sqlx::query!(
            "UPDATE guild_rule SET kick_safety_timeout=? WHERE guild_id=?",
            new_timeout,
            guild_id
        ),
    };

    match query.execute(pool).await {
        Ok(_) => {
            return Ok(CommandResponse::ephemeral_text(
                "Successfully set timeout!".to_owned(),
            ))
        }
        Err(why) => return Err(format!("Error while setting timeout: {why}")),
    }
}

async fn unset(
    ctx: &Context,
    guild_id: i64,
    timeout_type: TimeoutType,
) -> Result<Option<CommandResponse>, String> {
    // Safety timeout cannot be unset, and even though we shouldn't have received an interaction requesting this,
    // we will still check for it here.

    let type_map = ctx.data.read().await;
    let pool_holder: &DatabasePoolHolder = type_map.get::<DatabasePoolHolder>().unwrap();
    let pool = pool_holder.as_ref();

    let query = match timeout_type {
        TimeoutType::NewMember => sqlx::query!(
            "UPDATE guild_rule SET new_member_kick_timeout=NULL WHERE guild_id=?",
            guild_id
        ),
        TimeoutType::ImmunityRoleLoss => sqlx::query!(
            "UPDATE guild_rule SET loss_of_immunity_role_timeout=NULL WHERE guild_id=?",
            guild_id
        ),
        TimeoutType::Safety => return Err("Safety timeout cannot be unset".to_string()),
    };

    match query.execute(pool).await {
        Ok(_) => {
            return Ok(CommandResponse::ephemeral_text(
                "Successfully unset timeout!".to_owned(),
            ))
        }
        Err(why) => return Err(format!("Error while unsetting timeout: {why}")),
    }
}
