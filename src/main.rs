mod handler;

use std::path::Path;

use serenity::{framework::StandardFramework, prelude::*};
use sqlx::SqlitePool;

#[tokio::main]
async fn main() {
    // If running inside Docker, do not load dotenv file
    if std::env::var("NO_PERFORM_LOAD_ENV_FILE").is_err() { // not present -> load
        dotenvy::from_path(Path::new("CONFIG.env")).expect("Failed to load environment variables from CONFIG.env; set $NO_PERFORM_LOAD_ENV_FILE to disable");
    }

    let pool =
        SqlitePool::connect(&std::env::var("DATABASE_URL").expect("No $DATABASE_URL provided!"))
            .await
            .expect("Failed to connect to SQLite database!");
    sqlx::migrate!()
        .run(&pool)
        .await
        .expect("Failed to apply database migrations");

    let token = std::env::var("DISCORD_TOKEN").expect("No $DISCORD_TOKEN provided!");
    let intents = GatewayIntents::GUILD_MEMBERS;

    let mut client = Client::builder(&token, intents)
        .event_handler(handler::Handler)
        .framework(StandardFramework::new())
        .await
        .expect("Error creating client");

    if let Err(why) = client.start().await {
        println!("Client error: {:?}", why);
    }
}
