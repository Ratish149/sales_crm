# Quick Reference: Collection System

## API Endpoints

### Collections
```
GET    /api/collections/              # List all collections
POST   /api/collections/              # Create collection
GET    /api/collections/{slug}/       # Get collection by slug
PUT    /api/collections/{slug}/       # Update collection
DELETE /api/collections/{slug}/       # Delete collection
```

### Data (Nested under collection slug)
```
GET    /api/collections/{slug}/data/        # List all data for collection
POST   /api/collections/{slug}/data/        # Create data
GET    /api/collections/{slug}/data/{id}/   # Get specific data
PUT    /api/collections/{slug}/data/{id}/   # Update data
PATCH  /api/collections/{slug}/data/{id}/   # Partial update
DELETE /api/collections/{slug}/data/{id}/   # Delete data
```

## Field Types
- `text` - String
- `number` - Integer/Decimal
- `date` - YYYY-MM-DD
- `boolean` - true/false
- `email` - Email with validation

## Default Fields (Always Present)

Every collection automatically includes:
- **name** - Text field, required, filterable
- **slug** - Text field, optional, filterable
- **content** - Text field, optional

These fields cannot be used as custom field names.

## Example: Create Collection with Custom Fields
```json
POST /api/collections/
{
  "name": "Products",
  "fields": [
    {"name": "price", "type": "number", "required": true, "filterable": true},
    {"name": "category", "type": "text", "required": true, "filterable": true},
    {"name": "in_stock", "type": "boolean", "required": false, "filterable": true}
  ]
}
```

Response includes:
- `default_fields` - Built-in fields (name, content)
- `fields` - Your custom fields
- `all_fields` - Combined list with `is_default` flag
- Auto-generated `slug`: `"products"`

## Field Options
Each custom field can have:
- `name` - Field name (required, cannot be 'name' or 'content')
- `type` - Field type (required)
- `required` - Whether field is mandatory (default: false)
- `filterable` - Whether field can be used for filtering (default: false)

## Example: Add Data (with default + custom fields)
```json
POST /api/collections/products/data/
{
  "data": {
    "name": "Laptop",
    "content": "High-performance laptop with 16GB RAM",
    "price": 999.99,
    "category": "Electronics",
    "in_stock": true
  }
}
```

**Note:** `name` is required, `content` is optional.

## Example: Filter Data
```bash
# Filter by category
GET /api/collections/products/data/?category=Electronics

# Filter by in_stock
GET /api/collections/products/data/?in_stock=true

# Multiple filters
GET /api/collections/products/data/?category=Electronics&in_stock=true
```

## Example: Update Data
```json
PATCH /api/collections/products/data/1/
{
  "data": {
    "price": 899.99
  }
}
```

## Before Testing
1. Start PostgreSQL database
2. Run: `python manage.py migrate`
3. Run: `python manage.py runserver`
