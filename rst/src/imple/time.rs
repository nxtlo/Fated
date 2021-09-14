use std::time;
use humantime;
use chrono;

pub fn duration_to_humatime(dur: time::Duration) -> String {
    humantime::format_duration(dur).to_string().clone()
}

pub fn timestamp_to_iso(mut stamp: u64) -> String {
    if let None = Some(stamp) {
        stamp = 0;
    }
    let new_time = time::UNIX_EPOCH + time::Duration::new(stamp, 0);
    humantime::format_rfc3339(new_time).to_string()
}