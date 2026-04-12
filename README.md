## 🚀 Project Overview

The pipeline consists of the following stages:

1. **Reddit Data Extraction**
2. **Streaming with Apache Kafka**
3. **Data Storage with PostgreSQL/MySQL**
4. **Text Cleaning & Data Augmentation**
5. **Fine-Tuning a BERT Sentiment Classifier**
6. **Model Evaluation & Inference**
7. **Full Docker Support**

## 📥 1. Reddit Data Extraction

- Data is collected from the Reddit API using multiple subreddits grouped into **five categories**.
- The number of posts retrieved is customizable through the `TOTAL_LIMIT` variable.
- The project supports environment-based Reddit authentication using:

  ```env
  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_USER_AGENT
  REDDIT_USERNAME
  REDDIT_PASSWORD


## ⚡ 2. Real-Time Streaming with Apache Kafka

The pipeline leverages Apache Kafka to enable real-time data ingestion and processing.

This stage is composed of two main components:

📤 Kafka Producer
- Fetches Reddit posts dynamically using the Reddit API
- Streams each post as a message into a Kafka topic (reddit_posts)
- Controls the ingestion rate to avoid overwhelming the system
- Ensures scalability by decoupling data ingestion from downstream processing

Key responsibilities:

- Data ingestion from Reddit
- Message serialization (JSON)
- Publishing messages to Kafka topics


📥 Kafka Consumer
- Subscribes to the reddit_posts topic
- Consumes messages in batches for efficiency
- Stores raw data into the database (reddit_posts table)
- Applies preprocessing and data augmentation
- Publishes cleaned data into a new Kafka topic (cleaned_data)

Key responsibilities:

- Batch processing of streaming data
- Data persistence (raw + processed)
- Data cleaning and transformation
- Forwarding processed data for downstream tasks


🔄 Streaming Flow
Reddit API → Kafka Producer → Kafka Topic (reddit_posts)
           → Kafka Consumer → Database (raw data)
           → Data Cleaning & Augmentation
           → Kafka Topic (cleaned_data)


⚙️ Kafka Configuration

The pipeline supports both local execution and Docker-based environments.

# Kafka Configuration

# Kafka broker address
# Use "localhost:9092" for local execution
# Use "kafka:9092" when running with Docker
KAFKA_BROKER=

# Input topic (raw Reddit data)
KAFKA_TOPIC=reddit_posts

# Consumer group identifier (for scalability and fault tolerance)
KAFKA_CONSUMER_GROUP=reddit_consumer_group

# Output topic (processed/cleaned data)
TOPIC_OUTPUT=cleaned_data

# Consumer group ID (used internally by Kafka)
GROUP_ID=reddit_consumer_group


🧠 Design Considerations
- Decoupled Architecture: Producers and consumers operate independently
- Scalability: Multiple consumers can be added using the same GROUP_ID
- Fault Tolerance: Kafka ensures message durability and replayability
- Batch Processing: Improves performance and reduces database overhead
- Streaming + Processing Hybrid: Combines real-time ingestion with batch transformations


🚀 Why Kafka?

Using Apache Kafka allows this pipeline to:

Handle large-scale data ingestion
Enable real-time sentiment analysis pipelines
Support future extensions (e.g., monitoring, alerting, dashboards)
Integrate easily with distributed systems (Spark, Flink, etc.)


## 🗄️ 3. Data Storage with PostgreSQL / MySQL


The pipeline includes a flexible and scalable storage layer built on top of relational databases such as PostgreSQL and MySQL.

Database interactions are managed using SQLAlchemy, enabling seamless switching between database engines without modifying the core logic.

⚙️ Database Configuration

The system is fully configurable via environment variables:

# Database Configuration

# Supported values: "postgres" or "mysql"
DB_TYPE=

DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=


🔌 Connection Management
A centralized connection handler dynamically builds the database URL
Uses SQLAlchemy engine for efficient connection pooling
Ensures a single reusable connection instance across the pipeline
Supports both local and Docker-based environments


🧱 Data Model Overview
The pipeline stores data across multiple structured tables:


📥 reddit_posts (Raw Data)
Stores original Reddit data ingested from Kafka.
Fields:

- id (Primary Key)
- title
- text
- score
- num_comments
- created_utc
- url
- label (auto-generated)


👉 Labeling Strategy:
Rule-based labeling using subreddit categories
Fallback to sentiment analysis using VADER
Hybrid approach improves labeling robustness


🧹 cleaned_data (Processed Data)
Stores cleaned and normalized text ready for training.
Fields:

- id
- text
- label


🔄 relabeled_data (Hybrid Relabeling)
Stores dataset after applying model-based relabeling
Used to reduce noise and improve data quality before training


⚖️ balanced_* (Balanced Datasets)
Stores class-balanced datasets
Created using undersampling or other balancing strategies


🧪 synthetic_* (Augmented Data)
Stores synthetically generated samples
Used to improve minority class representation


📊 validation_data
Stores validation split (20% of dataset)
Includes both numeric and human-readable labels


📈 validation_results
Stores model predictions for validation data
Automatically resets before inserting new results


🧠 Data Processing Logic
- Raw messages from Kafka are stored immediately in reddit_posts
- Data validation filters:
  - Missing fields (id, text)
  - Non-informative text
- Hybrid labeling system:
  - Subreddit-based labeling
  - VADER sentiment fallback
- Cleaned data is stored in cleaned_data
- Additional transformations generate:
  - Relabeled datasets
  - Balanced datasets
  - Synthetic datasets


Kafka (reddit_posts)
        ↓
Database (reddit_posts - raw)
        ↓
Validation + Labeling (Hybrid)
        ↓
Database (cleaned_data)
        ↓
(Others)
   → relabeled_data: 
   → balanced_data:   Balance dataset distribution through oversampling, downsampling or both  
   → combined:    Combine relabeled and cleaned_data
   → synthetic_data:  Data generated by GPT-2 for oversampling