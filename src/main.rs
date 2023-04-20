mod handler;

use serenity::{framework::StandardFramework, prelude::*};
use sqlx::SqlitePool;

#[tokio::main]
async fn main() {
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
