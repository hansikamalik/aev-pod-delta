# Privacy Note – AEV AI Context Service

## Memory Privacy

The AEV AI Context Service stores user memory in an isolated manner using a unique user ID.

Each memory record is associated with a specific `user_id`. The API applies user-level isolation while accessing, updating, and deleting memory records.

This ensures that one user cannot access, modify, or delete another user's memory.

## Model Training

User memory stored by the AI Context Service is not used for model training.

The stored memory is used only to provide contextual information required by the application.

## Data Retention

Memory that has not been used for more than 90 days is eligible for automatic deletion through the memory expiry job.

The expiry process uses the `last_used_at` timestamp to identify inactive memory records.

## Security and Isolation

The service implements:

- User-level memory isolation
- Controlled memory CRUD operations
- Memory expiration after 90 days of inactivity
- Vector embeddings for contextual retrieval
- No sharing of memory between users
- No use of stored memory for model training