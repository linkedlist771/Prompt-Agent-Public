# Custom RAG Prompt Reference - Claude Library

This module provides functionality for importing and managing Claude prompts in your custom RAG (Retrieval-Augmented Generation) database.

## Overview

The `claude_lib` module enables you to:
- Import Claude prompt collections into your vector database
- Process and vectorize prompts for semantic search
- Support both system prompts and user prompts
- Maintain metadata for better prompt organization

## Features

### 🔄 Claude Prompt Import
- **Automatic Import**: Import Claude prompts from JSON collections
- **Smart Prompt Selection**: Prioritizes system prompts over user prompts
- **Metadata Preservation**: Maintains title, URL, and prompt type information
- **Batch Processing**: Efficient bulk import into vector database

### 📚 Prompt Collection Management
- **JSON Format Support**: Process standardized prompt collections
- **Vector Database Integration**: Seamless integration with the RAG system
- **Search Optimization**: Optimized for semantic similarity search

## File Structure

```
prompts_crawler/claude_lib/
├── __init__.py                 # Module initialization
├── crawler.py                 # Web scraping functionality
├── import_claude_prompts.py   # Main import script
├── prompts.json              # Claude prompt collection
├── prompts.md                # Markdown version of prompts
└── README.md                 # This documentation
```

## Quick Start

### 1. Import Claude Prompts

Run the import script to add Claude prompts to your vector database:

```bash
cd prompts_crawler/claude_lib/
python import_claude_prompts.py
```

### 2. Programmatic Usage

Import prompts programmatically in your code:

```python
from prompts_crawler.claude_lib.import_claude_prompts import import_claude_prompts

# Import all Claude prompts
import_claude_prompts()
```

## Import Process

The import process follows these steps:

1. **Read JSON Collection**: Loads prompts from `prompts.json`
2. **Smart Content Selection**: 
   - Prioritizes `system_prompt` if available
   - Falls back to `user_prompt` if no system prompt
   - Skips empty prompts with warnings
3. **Metadata Creation**: Preserves prompt metadata including:
   - Title and URL
   - Source identification
   - Prompt type indicators
4. **Vector Database Storage**: Batch inserts into the vector database
5. **Verification**: Reports import success and database statistics

## Prompt JSON Format

The expected JSON format for Claude prompts:

```json
[
  {
    "title": "Prompt Title",
    "url": "https://example.com/prompt",
    "system_prompt": "You are a helpful assistant that...",
    "user_prompt": "Please help me with..."
  }
]
```

### Required Fields
- `title`: Human-readable prompt name
- Either `system_prompt` or `user_prompt` (or both)

### Optional Fields
- `url`: Source URL for the prompt
- Additional metadata fields

## Integration with RAG System

Once imported, the Claude prompts become part of your RAG system:

### Semantic Search
```python
from prompt_agent.vector_db.prompt_vector_db import get_prompt_vector_db

vector_db = get_prompt_vector_db()

# Search for relevant prompts
results = vector_db.query(
    query_texts=["help me write code"],
    n_results=5
)
```

### Metadata Filtering
```python
# Search only Claude prompts
results = vector_db.query(
    query_texts=["creative writing"],
    n_results=3,
    where={"source": "claude_lib"}
)
```

## Advanced Usage

### Custom Import Parameters

Modify the import script for custom behavior:

```python
def custom_import_claude_prompts(json_file="custom_prompts.json", source_name="custom"):
    """Custom import with different parameters"""
    # Read from custom JSON file
    with open(json_file, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)
    
    # Process with custom source name
    for i, prompt in enumerate(prompts_data):
        # Custom processing logic
        pass
```

### Batch Processing Large Collections

For large prompt collections:

```python
def batch_import_prompts(prompts_data, batch_size=100):
    """Import prompts in batches for better performance"""
    vector_db = get_prompt_vector_db()
    
    for i in range(0, len(prompts_data), batch_size):
        batch = prompts_data[i:i + batch_size]
        # Process batch
        documents, metadatas, ids = process_batch(batch)
        vector_db.add(documents=documents, metadatas=metadatas, ids=ids)
```

## Monitoring and Logging

The import process uses structured logging:

```python
from loguru import logger

# Import with detailed logging
logger.info("Starting Claude prompts import...")
import_claude_prompts()
logger.info("Import completed successfully")
```

### Log Messages
- **Info**: Successful imports and statistics
- **Warning**: Skipped empty prompts
- **Error**: Import failures and file issues

## Best Practices

### Prompt Quality
- ✅ Ensure prompts have clear, actionable content
- ✅ Include both system and user prompts when available
- ✅ Maintain consistent JSON formatting
- ✅ Add meaningful titles and metadata

### Performance Optimization
- ✅ Use batch imports for large collections
- ✅ Monitor vector database size and performance
- ✅ Regularly clean up unused or outdated prompts
- ✅ Consider prompt deduplication

### Data Management
- ✅ Backup your prompt collections regularly
- ✅ Version control your JSON files
- ✅ Document custom prompt sources
- ✅ Test imports in development environments

## Troubleshooting

### Common Issues

**Q: Import fails with JSON decode error**
- Verify JSON file syntax and encoding (UTF-8)
- Check for trailing commas or malformed JSON

**Q: Prompts not appearing in search**
- Confirm vector database connection
- Check if prompts were actually imported (see logs)
- Verify search query parameters

**Q: Empty prompts being skipped**
- Check that prompts have either `system_prompt` or `user_prompt`
- Review the warning logs for specific prompt titles

### Debug Mode

Enable debug logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run import with debug output
import_claude_prompts()
```

## Integration with Browser Extension

The imported prompts automatically become available in the Prompt Agent browser extension:

1. **Real-time Access**: Prompts are searchable from the extension
2. **Context Injection**: Relevant prompts suggested based on current conversation
3. **Semantic Matching**: Advanced similarity search finds the best prompts

## API Access

Access imported prompts via the REST API:

```bash
# Search prompts
curl -X POST "http://localhost:3648/vector-db/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "help with coding", "limit": 5}'

# Get prompt by ID
curl "http://localhost:3648/vector-db/prompts/claude_prompt_0"
```

## Contributing

To contribute new Claude prompt collections:

1. Format prompts according to the JSON schema
2. Test import functionality
3. Add appropriate metadata
4. Submit via pull request

## Support

- 📖 Main Documentation: [Root README](../../README.md)
- 🔧 Vector DB Documentation: [Vector Database Guide](../../prompt_agent/vector_db/README.md)
- 🐛 Issues: Submit via GitHub Issues

---

**Note**: This module is part of the larger Prompt Agent RAG system. Ensure the main system is properly configured before importing prompts. 