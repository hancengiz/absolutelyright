use axum::{
    routing::{get, post},
    Router, Json,
    middleware,
    http::Request,
    response::Response,
};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, net::SocketAddr, sync::Arc};
use tower_http::services::ServeDir;
use tokio_rusqlite::Connection;
use std::fs::OpenOptions;
use std::io::Write;
use chrono::Utc;
use std::env;

#[derive(Clone, Debug, Serialize, Deserialize)]
struct DayCount {
    day: String,
    count: u32,
    right_count: u32,
}

#[tokio::main]
async fn main() {
    // Initialize SQLite database - use /app/data on Fly.io, local file otherwise
    let db_path = if std::path::Path::new("/app/data").exists() {
        "/app/data/counts.db"
    } else {
        "counts.db"
    };
    let db = Connection::open(db_path).await.unwrap();
    
    // Create table if it doesn't exist
    db.call(|conn| {
        conn.execute(
            "CREATE TABLE IF NOT EXISTS day_counts (
                day TEXT PRIMARY KEY,
                count INTEGER NOT NULL,
                right_count INTEGER DEFAULT 0
            )",
            [],
        )?;
        // Add right_count column if it doesn't exist (for existing databases)
        let _ = conn.execute(
            "ALTER TABLE day_counts ADD COLUMN right_count INTEGER DEFAULT 0",
            [],
        );
        Ok(())
    })
    .await
    .unwrap();

    let db = Arc::new(db);

    // Build router
    let app = Router::new()
        .route("/api/today", get(get_today))
        .route("/api/history", get(get_history))
        .route("/api/set", post(set_day))
        // Serve static files from ./frontend
        .nest_service("/", ServeDir::new("frontend"))
        .layer(middleware::from_fn(log_pageview))
        .with_state(db);

    let addr = SocketAddr::from(([0, 0, 0, 0], 3003));
    println!("listening on http://{}", addr);
    axum::serve(tokio::net::TcpListener::bind(addr).await.unwrap(), app)
        .await
        .unwrap();
}

async fn get_today(
    state: axum::extract::State<Arc<Connection>>,
) -> Json<HashMap<&'static str, u32>> {
    let today = Utc::now().format("%Y-%m-%d").to_string();
    
    let (count, right_count) = state
        .call(move |conn| {
            let mut stmt = conn.prepare("SELECT count, right_count FROM day_counts WHERE day = ?1")?;
            let result = stmt.query_row([&today], |row| {
                Ok((row.get::<_, u32>(0)?, row.get::<_, u32>(1).unwrap_or(0)))
            }).unwrap_or((0, 0));
            Ok(result)
        })
        .await
        .unwrap();

    let mut map = HashMap::new();
    map.insert("count", count);
    map.insert("right_count", right_count);
    Json(map)
}

async fn get_history(
    state: axum::extract::State<Arc<Connection>>,
) -> Json<Vec<DayCount>> {
    let history = state
        .call(|conn| {
            let mut stmt = conn.prepare("SELECT day, count, right_count FROM day_counts ORDER BY day")?;
            let days = stmt
                .query_map([], |row| {
                    Ok(DayCount {
                        day: row.get(0)?,
                        count: row.get(1)?,
                        right_count: row.get(2).unwrap_or(0),
                    })
                })?
                .collect::<Result<Vec<_>, _>>()?;
            Ok(days)
        })
        .await
        .unwrap();

    Json(history)
}

#[derive(Deserialize)]
struct SetRequest {
    day: String,
    count: u32,
    right_count: Option<u32>,
    secret: Option<String>,
}

async fn set_day(
    state: axum::extract::State<Arc<Connection>>,
    Json(payload): Json<SetRequest>,
) -> Result<Json<&'static str>, (axum::http::StatusCode, &'static str)> {
    // Check secret if ABSOLUTELYRIGHT_SECRET is set
    if let Ok(expected_secret) = env::var("ABSOLUTELYRIGHT_SECRET") {
        match payload.secret {
            Some(provided_secret) if provided_secret == expected_secret => {
                // Secret matches, continue
            }
            _ => {
                // No secret provided or wrong secret
                return Err((axum::http::StatusCode::UNAUTHORIZED, "Invalid secret"));
            }
        }
    }
    // If ABSOLUTELYRIGHT_SECRET is not set, allow access (for local dev)
    
    let right_count = payload.right_count.unwrap_or(0);
    state
        .call(move |conn| {
            conn.execute(
                "INSERT INTO day_counts (day, count, right_count) VALUES (?1, ?2, ?3)
                 ON CONFLICT(day) DO UPDATE SET count = ?2, right_count = ?3",
                [&payload.day, &payload.count.to_string(), &right_count.to_string()],
            )?;
            Ok(())
        })
        .await
        .unwrap();

    Ok(Json("ok"))
}

async fn log_pageview(
    req: Request<axum::body::Body>,
    next: middleware::Next,
) -> Response<axum::body::Body> {
    let path = req.uri().path().to_string();
    let method = req.method().to_string();
    
    // Only log GET requests to main page
    if method == "GET" && (path == "/" || path == "/index.html") {
        let timestamp = Utc::now().format("%Y-%m-%d %H:%M:%S").to_string();
        let log_entry = format!("{} - Pageview: {}\n", timestamp, path);
        
        // Append to log file - use /app/data on Fly.io, local file otherwise
        let log_path = if std::path::Path::new("/app/data").exists() {
            "/app/data/pageviews.log"
        } else {
            "pageviews.log"
        };
        
        if let Ok(mut file) = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_path)
        {
            let _ = file.write_all(log_entry.as_bytes());
        }
    }
    
    next.run(req).await
}