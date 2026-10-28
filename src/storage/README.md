# Storage Module

This module handles data persistence across AWS services:

## Components

### S3Storage (`s3_storage.py`)
- Manages S3 bucket operations for data storage
- Handles upload/download operations
- Manages bucket lifecycle and policies

### Repository (`repository.py`)
- Generic data repository pattern implementation
- Abstracts storage backends
- Provides CRUD operations for various data types