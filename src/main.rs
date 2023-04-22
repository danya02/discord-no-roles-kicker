mod handler;

use std::path::Path;

use serenity::{framework::StandardFramework, prelude::*};
use sqlx::SqlitePool;

#[derive(Clone, Debug)]
struct DatabasePoolHolder {
    pub pool: SqlitePool,
}

impl AsRef<SqlitePool> for DatabasePoolHolder {
    fn as_ref(&self) -> &SqlitePool {
        &self.pool
    }
}

impl AsMut<SqlitePool> for DatabasePoolHolder {
    fn as_mut(&mut self) -> &mut SqlitePool {
        &mut self.pool
    }
}

impl DatabasePoolHolder {
    fn new(pool: SqlitePool) -> Self {
        Self { pool }
    }
}

impl TypeMapKey for DatabasePoolHolder {
    type Value = DatabasePoolHolder;
}

#[tokio::main]
async fn main() {
    // If running inside Docker, do not load dotenv file
    if std::env::var("NO_PERFORM_LOAD_ENV_FILE").is_err() {
        // not present -> load
        dotenvy::from_path(Path::new("CONFIG.env")).expect("Failed to load environment variables from CONFIG.env; set $NO_PERFORM_LOAD_ENV_FILE to disable");
    }

    tracing_subscriber::fmt::init();

    let pool =
        SqlitePool::connect(&std::env::var("DATABASE_URL").expect("No $DATABASE_URL provided!"))
            .await
            .expect("Failed to connect to SQLite database!");

    sqlx::migrate!()
        .run(&pool)
        .await
        .expect("Failed to apply database migrations");

    let holder = DatabasePoolHolder::new(pool);

    let token = std::env::var("DISCORD_TOKEN").expect("No $DISCORD_TOKEN provided!");
    let intents = GatewayIntents::GUILD_MEMBERS
        | GatewayIntents::MESSAGE_CONTENT
        | GatewayIntents::GUILD_MESSAGES
        | GatewayIntents::GUILDS;

    let mut client = Client::builder(&token, intents)
        .event_handler(handler::Handler)
        .type_map_insert::<DatabasePoolHolder>(holder)
        .framework(StandardFramework::new())
        .await
        .expect("Error creating client");

    if let Err(why) = client.start().await {
        println!("Client error: {why:?}");
    }
}
