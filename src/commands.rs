use serenity::model::application::interaction::application_command::ApplicationCommandInteraction;
use serenity::{model::prelude::command::Command, prelude::Context};
use tracing::error;

mod channel;
mod setup;
mod show_rule;

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
    if let Err(why) = Command::create_global_application_command(&ctx.http, |command| {
        setup::register(command);
        show_rule::register(command);
        channel::system_register(command);
        command
    })
    .await
    {
        error!("Failed to create global commands: {why}");
    }
}

pub async fn dispatch(ctx: Context, command: ApplicationCommandInteraction) {
    let result = match command.data.name.as_str() {
        "setup" => setup::run(&ctx, &command).await,
        "rule" => show_rule::run(&ctx, &command).await,
        "syschannel" => channel::system_run(&ctx, &command).await,
        other => {
            error!("Interaction command not implemented: {other}");
            Err("Interaction command not implemented; this is a bug in the bot.".to_owned())
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
