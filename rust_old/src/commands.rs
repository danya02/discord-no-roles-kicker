use serenity::model::application::interaction::application_command::ApplicationCommandInteraction;
use serenity::{model::prelude::command::Command, prelude::Context};
use tracing::*;

mod channel;
mod setup;
mod show_rule;
mod timeout;

#[derive(Clone, Debug)]
pub struct CommandResponse {
    pub text: String,
    pub ephemeral: bool,
}

impl CommandResponse {
    fn text(text: String) -> Option<Self> {
        Some(Self {
            text,
            ephemeral: false,
        })
    }

    fn ephemeral_text(text: String) -> Option<Self> {
        Some(Self {
            text,
            ephemeral: true,
        })
    }
}

pub async fn setup_commands(ctx: &Context) {
    info!("Starting creation of application commands");
    let mut results = vec![];
    results.push(
        Command::create_global_application_command(&ctx.http, |command| {
            setup::register(command);
            command
        })
        .await,
    );
    results.push(
        Command::create_global_application_command(&ctx.http, |command| {
            show_rule::register(command);
            command
        })
        .await,
    );

    results.push(
        Command::create_global_application_command(&ctx.http, |command| {
            channel::system_register(command);
            command
        })
        .await,
    );

    results.push(
        Command::create_global_application_command(&ctx.http, |command| {
            channel::notify_register(command);
            command
        })
        .await,
    );

    results.push(
        Command::create_global_application_command(&ctx.http, |command| {
            timeout::new_register(command);
            command
        })
        .await,
    );

    results.push(
        Command::create_global_application_command(&ctx.http, |command| {
            timeout::immunity_register(command);
            command
        })
        .await,
    );

    results.push(
        Command::create_global_application_command(&ctx.http, |command| {
            timeout::safety_register(command);
            command
        })
        .await,
    );

    for res in results {
        if let Err(why) = res {
            error!("Error while creating command: {why}");
        }
    }
}

pub async fn dispatch(ctx: Context, command: ApplicationCommandInteraction) {
    let result = match command.data.name.as_str() {
        "setup" => setup::run(&ctx, &command).await,
        "rule" => show_rule::run(&ctx, &command).await,
        "syschannel" => channel::system_run(&ctx, &command).await,
        "pendingchannel" => channel::notify_run(&ctx, &command).await,
        "newtimeout" => timeout::run(&ctx, &command, timeout::TimeoutType::NewMember).await,
        "immunitytimeout" => {
            timeout::run(&ctx, &command, timeout::TimeoutType::ImmunityRoleLoss).await
        }
        "safetytimeout" => timeout::run(&ctx, &command, timeout::TimeoutType::Safety).await,

        other => {
            error!("Interaction command not implemented: {other}");
            Err(format!(
                "Interaction command for `{other}` is not implemented; this is a bug in the bot."
            ))
        }
    };

    match result {
        Err(why) => {
            error!("Error while performing interaction: {why}");
            if let Err(why2) = command.create_interaction_response(&ctx.http, |resp|{
            resp.kind(serenity::model::prelude::interaction::InteractionResponseType::ChannelMessageWithSource)
            .interaction_response_data(|msg| msg.content(why).ephemeral(true))
        }).await {
                error!("Also error responding: {why2}");
            }
        }
        Ok(result) => {
            if let Some(res) = result {
                if let Err(why2) = command.create_interaction_response(&ctx.http, |resp|{
                    resp.kind(serenity::model::prelude::interaction::InteractionResponseType::ChannelMessageWithSource)
                    .interaction_response_data(|msg| {
                        msg.content(res.text.clone()).ephemeral(res.ephemeral)
                })
                }).await {
                        error!("Error responding: {why2}");
                    }
            }
        }
    }
}
