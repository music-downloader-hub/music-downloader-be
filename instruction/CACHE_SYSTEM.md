# Disk Cache Management System

## Overview

The Disk Cache Management System provides automatic management of downloaded audio files with TTL (Time To Live) and LRU (Least Recently Used) eviction policies. This prevents disk overflow while maintaining fast access to frequently used content.

## Features

### ✅ Implemented Features

- **TTL Management**: Directories automatically expire after configurable time
- **LRU Eviction**: Least recently used directories are removed when quota is exceeded
- **Redis Tracking**: All cache metadata stored in Redis for scalability
- **Background Cleanup**: Automatic periodic cleanup and quota enforcement
- **API Management**: RESTful API for cache monitoring and control
- **Auto Registration**: Completed downloads automatically registered in cache

### 🔧 Configuration

Configure in `app/setting/setting.py`:

```python
# Disk Cache Management
ENABLE_DISK_CACHE_MANAGEMENT = True  # Enable/disable cache system
DISK_CACHE_TTL_SECONDS = 86400  # 24 hours TTL for directories
DISK_CACHE_MAX_BYTES = 10 * 1024 * 1024 * 1024  # 10GB default quota
DISK_CACHE_CLEANUP_INTERVAL = 3600  # 1 hour cleanup interval
DISK_CACHE_LRU_EVICTION_THRESHOLD = 0.9  # Start eviction at 90% quota
```

## Redis Keys Structure

### Directory TTL Tracking
- **Key**: `dir:{relative_path}`
- **Type**: String with TTL
- **Value**: Timestamp when directory was registered
- **TTL**: `DISK_CACHE_TTL_SECONDS`

### LRU Tracking
- **Key**: `cache:lru`
- **Type**: ZSET (Sorted Set)
- **Score**: Last access timestamp
- **Member**: Relative directory path

### Cache Size Tracking
- **Key**: `cache:bytes`
- **Type**: String
- **Value**: Total bytes used by all cached directories

### Directory Locks
- **Key**: `lock:dir:{relative_path}`
- **Type**: String
- **Value**: "locked"
- **Purpose**: Prevent concurrent operations on same directory

## API Endpoints

### Cache Statistics
```http
GET /cache/stats
```
Returns current cache usage statistics.

### List Cached Directories
```http
GET /cache/directories?limit=100
```
Lists all cached directories with their information.

### Get Directory Info
```http
GET /cache/directories/{path}
```
Get detailed information about a specific cached directory.

### Manual Cleanup
```http
POST /cache/cleanup
```
Run manual cache cleanup and quota enforcement.

### Scheduler Control
```http
POST /cache/start-scheduler
POST /cache/stop-scheduler
```
Start/stop the background cache scheduler.

### Manual Registration
```http
POST /cache/register/{path}
```
Manually register a directory in the cache system.

### Remove Directory
```http
DELETE /cache/directories/{path}?remove_files=false
```
Remove directory from cache tracking, optionally from disk.

## Usage Examples

### Check Cache Status
```bash
curl http://localhost:8080/cache/stats
```

### List Cached Directories
```bash
curl http://localhost:8080/cache/directories
```

### Run Manual Cleanup
```bash
curl -X POST http://localhost:8080/cache/cleanup
```

### Start Background Scheduler
```bash
curl -X POST http://localhost:8080/cache/start-scheduler
```

## How It Works

### 1. Download Registration
When a download completes:
1. `DownloadService.register_completed_download()` is called
2. Finds the most recently created directory
3. Registers it in cache with current timestamp
4. Updates LRU tracking and size counters

### 2. TTL Management
- Each directory gets a TTL when registered
- TTL is extended when directory is accessed
- Expired directories are automatically removed during cleanup

### 3. LRU Eviction
- When cache usage exceeds threshold (90% by default)
- Oldest accessed directories are removed first
- Continues until usage drops to 80% of quota

### 4. Background Cleanup
- `CacheScheduler` runs every hour by default
- Cleans up expired directories
- Enforces quota limits
- Updates cache statistics

## Testing

Run the test script to verify functionality:

```bash
cd backend_python
python test_cache.py
```

This will test:
- Cache service initialization
- Statistics retrieval
- Directory listing
- Scheduler functionality
- Directory operations

## Monitoring

### Cache Statistics
Monitor cache usage through the API:
- Total bytes used
- Number of cached directories
- Usage percentage
- Quota status

### Logs
The system logs important events:
- Directory registration
- Cache cleanup operations
- Quota enforcement
- Error conditions

## Performance Considerations

### Redis Operations
- Uses Redis pipelines for batch operations
- Local caching reduces Redis calls
- Connection pooling for better performance

### Disk Operations
- Directory size calculation is cached
- File operations are done in background
- Locks prevent concurrent modifications

### Memory Usage
- Minimal memory footprint
- Redis stores only metadata, not file content
- Automatic cleanup prevents memory leaks

## Troubleshooting

### Common Issues

1. **Cache not working**
   - Check `ENABLE_DISK_CACHE_MANAGEMENT = True`
   - Verify Redis connection
   - Check downloads directory exists

2. **High memory usage**
   - Reduce `DISK_CACHE_MAX_BYTES`
   - Lower `DISK_CACHE_TTL_SECONDS`
   - Run manual cleanup

3. **Directories not being cleaned**
   - Check scheduler is running
   - Verify TTL settings
   - Run manual cleanup

### Debug Commands

```bash
# Check Redis keys
redis-cli keys "dir:*"
redis-cli keys "cache:*"

# Check cache stats
curl http://localhost:8080/cache/stats

# Run manual cleanup
curl -X POST http://localhost:8080/cache/cleanup
```

## Future Enhancements

- [ ] Configurable eviction policies (LFU, FIFO)
- [ ] Cache warming strategies
- [ ] Integration with object storage
- [ ] Advanced monitoring and alerting
- [ ] Cache hit/miss statistics
- [ ] Directory compression support
