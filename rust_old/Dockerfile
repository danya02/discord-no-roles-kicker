FROM lukemathwalker/cargo-chef:latest-rust-slim-buster AS chef
WORKDIR /app

FROM chef AS planner
# Prepare the database by installing SQLx CLI and applying the migrations
# The database is necessary as SQLx executes queries against it at compile time
# Requires OpenSSL
RUN apt-get update && apt-get install -y libssl-dev pkg-config && rm -rf /var/lib/apt
RUN cargo install sqlx-cli
COPY . .
ENV DATABASE_URL=sqlite:/tmp/database.db
RUN sqlx database setup
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS builder 
COPY --from=planner /app/recipe.json recipe.json
# Build dependencies - this is the caching Docker layer!
RUN cargo chef cook --release --recipe-path recipe.json
# Build application
# Use the prepared database as it needs to be present when building
COPY . .
COPY --from=planner /tmp/database.db /tmp/database.db
ENV DATABASE_URL=sqlite:/tmp/database.db
RUN cargo build --release

# We do not need the Rust toolchain to run the binary!
FROM debian:buster-slim AS runtime
WORKDIR /app
COPY --from=builder /app/target/release/discord-no-roles-kicker /usr/local/bin
ENTRYPOINT ["/usr/local/bin/discord-no-roles-kicker"]