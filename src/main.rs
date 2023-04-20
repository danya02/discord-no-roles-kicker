use sqlx::SqlitePool;

#[tokio::main]
async fn main() {
    let pool = SqlitePool::connect(&std::env::var("DATABASE_URL").expect("No $DATABASE_URL provided!")).await.expect("Failed to connect to SQLite database!");
    sqlx::migrate!().run(&pool).await.expect("Failed to apply database migrations");
    println!("Hello, world!");
}
