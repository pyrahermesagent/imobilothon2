# Database Model Specification Document
*A comprehensive guide and template for documenting your full-stack application's database architecture.*

Use mermaid.js for UML diagrams

---

## 1. Project & System Overview
Define the context of the database to ensure all stakeholders understand its purpose and scope.
* **System Name:** [Name of your Full-Stack Application]
* **Version:** [e.g., 1.0.0]
* **Author/Lead Data Architect:** [Your Name]
* **Description:** A brief summary of what the application does and the primary role of this database (e.g., "A multi-tenant SaaS application database handling user authentication, billing, and real-time messaging").

## 2. Database Architecture & Technology Stack
Specify the foundational technologies and architectural decisions.
* **Database Type:** [e.g., Relational (SQL), Document-based (NoSQL), Graph, Key-Value]
* **DBMS (Database Management System):** [e.g., PostgreSQL 15, MongoDB 6.0, MySQL 8, Redis]
* **Hosting/Cloud Provider:** [e.g., AWS RDS, MongoDB Atlas, Supabase, self-hosted Docker]
* **ORM / Query Builder:** [e.g., Prisma, TypeORM, Entity Framework, SQLAlchemy, Drizzle]
* **Migration Tool:** [e.g., Flyway, Liquibase, Alembic, Prisma Migrate]

## 3. Global Naming Conventions & Standards
Establish strict rules to maintain consistency across the schema.
* **Tables/Collections:** `snake_case` and plural (e.g., `users`, `order_items`) OR `PascalCase` and singular (e.g., `User`, `OrderItem`). *(Pick one and stick to it).*
* **Columns/Fields:** `snake_case` (e.g., `created_at`, `first_name`).
* **Primary Keys:** Always named `id` (UUID or BigInt Auto-increment) or `table_name_id`.
* **Foreign Keys:** `[related_table_singular]_id` (e.g., `user_id`, `product_id`).
* **Boolean Fields:** Prefix with `is_`, `has_`, or `can_` (e.g., `is_active`, `has_premium`).
* **Timestamps:** Every table must include `created_at` and `updated_at`. Include `deleted_at` if implementing soft deletes.

## 4. Entity-Relationship Diagram (ERD)
*Provide a visual representation of your database structure.*
* **Link to Diagram:** [Insert link to Lucidchart, Draw.io, Eraser.io, or dbdiagram.io]
* *(Optional)* Provide DBML (Database Markup Language) code here for quick reference.

## 5. Core Entities (Data Dictionary)
Document every table/collection, its purpose, and its attributes. 

### 5.1. Entity: `users`
**Description:** Stores core authentication and profile data for all application users.

| Column Name | Data Type | Constraints / Modifiers | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY, Default: gen_random_uuid() | Unique identifier for the user. |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | User's email address used for login. |
| `password_hash` | VARCHAR(255) | NOT NULL | Bcrypt/Argon2 hashed password. |
| `role` | ENUM | NOT NULL, Default: 'USER' | Defines RBAC level (e.g., USER, ADMIN). |
| `is_verified` | BOOLEAN | NOT NULL, Default: FALSE | Whether the user verified their email. |
| `created_at` | TIMESTAMP | NOT NULL, Default: NOW() | Record creation timestamp. |
| `updated_at` | TIMESTAMP | NOT NULL, Default: NOW() | Auto-updates on modification. |
| `deleted_at` | TIMESTAMP | NULL | Used for soft-deleting accounts. |

### 5.2. Entity: `orders` *(Example 2)*
**Description:** Tracks customer purchases and current fulfillment status.

| Column Name | Data Type | Constraints / Modifiers | Description |
| :--- | :--- | :--- | :--- |
| `id` | BIGSERIAL | PRIMARY KEY | Sequential order ID. |
| `user_id` | UUID | FOREIGN KEY (users.id) | The user who placed the order. |
| `total_amount`| DECIMAL(10,2)| NOT NULL | Total cost including tax. |
| `status` | ENUM | NOT NULL, Default: 'PENDING' | Status: PENDING, PAID, SHIPPED, CANCELED. |

*(Repeat this structure for all tables: `products`, `sessions`, `payments`, etc.)*

## 6. Relationships & Cardinality
Explicitly map out how entities interact, detailing cascade behaviors.

* **Users to Orders (1:N):** One `user` can have many `orders`.
  * *Foreign Key:* `orders.user_id` -> `users.id`
  * *On Delete:* `RESTRICT` (Cannot delete a user if they have associated orders).
* **Orders to Products (M:N):** Many `orders` contain many `products`.
  * *Junction Table:* `order_items`
  * *Foreign Keys:* `order_items.order_id` & `order_items.product_id`
  * *On Delete:* `CASCADE` (If order is deleted, delete its line items).
* **Users to User_Profiles (1:1):** Separation of auth data from profile details.
  * *Foreign Key:* `user_profiles.user_id` -> `users.id` (UNIQUE constraint).

## 7. Indexing & Performance Strategy
Document keys and indexes to ensure fast query execution.
* **Primary Key Indexes:** Automatically created on all `id` columns.
* **Foreign Key Indexes:** Must be explicitly created on all foreign key columns (e.g., `user_id` in `orders`) to optimize JOIN operations.
* **Unique Indexes:** e.g., `users(email)` for fast duplicate-check lookups.
* **Composite Indexes:** e.g., `CREATE INDEX idx_user_status ON users (role, is_active)` for frequent dashboard filtering.
* **Text Search:** Define if any columns require Full-Text Search (FTS) indexes (e.g., `products.description`).

## 8. Security & Data Compliance
Outline how sensitive data is protected.
* **Data Encryption at Rest:** Handled via cloud provider (e.g., AWS KMS) or database-level TDE (Transparent Data Encryption).
* **Row-Level Security (RLS):** [Specify if used, e.g., "PostgreSQL RLS policies enabled so users can only `SELECT` their own `orders`."]
* **PII (Personally Identifiable Information):** Columns like `ssn`, `date_of_birth`, or `credit_card_token` must be documented and heavily restricted.
* **Soft Deletes vs. Hard Deletes:** Data retention policy (e.g., GDPR right-to-be-forgotten compliance).

## 9. Seed Data & Environments
* **Development/Local:** Use dummy data generators (Faker.js) to populate 1,000+ records for UI testing.
* **Staging:** Anonymized snapshot of the production database for integration testing.
* **Production Seed:** Minimal essential data required to run the app (e.g., default Admin user, system ENUM tables, default settings).

## 10. Future Scalability Considerations
* **Sharding/Partitioning:** e.g., "If `audit_logs` exceeds 100M rows, we will partition by month."
* **Read Replicas:** e.g., "Heavy reporting queries will be routed to a Read Replica instance."
* **Caching Layer:** e.g., "Redis will be utilized to cache user session tokens and top 100 accessed products."
