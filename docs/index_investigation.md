# Investigating Index Patterns

**LLM response when asked about indexing strategies for our query patterns:**

Because you are on MongoDB Atlas with millions of documents, you have a major advantage: Atlas Search (Lucene) is built right into your cluster.
However, since you want to stick to standard database indexes for these "basic" queries, the mandatory customer filter completely changes the strategy. It acts as a massive bottleneck reducer.

## The Strategy: "Customer-First" Compound Indexes

Since every query starts with customer, your indexes must always lead with it. Because the customer filter narrows the result set down to a handful or a few thousand documents, those documents will easily fit into MongoDB's 32 MB in-memory sort buffer.
Instead of creating 10 different compound indexes (which will bloat your RAM and slow down writes), you can use a hybrid index strategy.

## Implementation Plan #1. The Multi-Purpose "Filter + Sort" Index (For High-Volume Columns)

Identify the 2 or 3 most common columns users sort by (e.g., createdAt or status). Create dedicated compound indexes for these to guarantee instant, index-backed sorting.

```
// Index 1: For the default view sorted by date
db.collection.createIndex({ customerId: 1, createdAt: -1 })
```
```
// Index 2: For the secondary view sorted by status
db.collection.createIndex({ customerId: 1, status: 1 })
```

## 2. The Universal "Catch-All" Index (For the Other 7-8 Columns)

For the remaining, rarely sorted columns (e.g., billingZip, assignedTo), do not create dedicated indexes. Instead, rely on a single index that optimizes the filtering step, and let MongoDB sort the small leftover pool in memory.

```
// Index 3: The Catch-All
db.collection.createIndex({ customerId: 1 })
```

How MongoDB executes a query on a rare column (e.g., sorting by billingZip):

   1. MongoDB uses Index 3 to instantly fetch the few hundred or thousand documents belonging to that customerId.
   2. It pulls those specific documents into RAM.
   3. It performs an in-memory sort on billingZip. Because a few thousand documents take up only a few kilobytes or megabytes, it safely stays way under the 32 MB limit.

## ⚠️ The Dangerous Edge Case: "The Mega-Customer"

This strategy works perfectly unless you have a "Mega-Customer" who owns hundreds of thousands of documents.
If a user filters by a Mega-Customer and sorts by one of the 8 unindexed columns, MongoDB will try to pull all those hundreds of thousands of documents into RAM to sort them. This will instantly trigger the 32 MB memory limit error and crash the query.

## How to protect against the Mega-Customer:

* Enforce Pagination: Always append .limit(100) or smaller to your grid queries. (Note: Limit only prevents the error if MongoDB can use an index to sort. If it has to sort in memory, it still has to load all matching documents before it can figure out the top 100).
* Leverage Atlas Search (The No-Index Alternative): Since you are already on Atlas, you can create a single Atlas Search Index mapping your 10 columns. Lucene handles arbitrary sorting natively. It handles both small and mega-customers identically without requiring any compound B-tree indexes or risking 32 MB RAM crashes.

### Mega-Customer + "Skip" pagination issues

The combination of Mega-Customers and Offset Pagination (.skip()) creates a worst-case performance scenario for MongoDB standard indexes.
If a user opens a Mega-Customer's account, goes to page 10 (.skip(200)), and sorts by one of your 8 unindexed columns, MongoDB must load every single document for that customer into RAM to sort them before it can skip the first 200. This will instantly trigger the 32 MB memory limit error and crash the UI.

Because you are on MongoDB Atlas, you should move away from standard B-Tree indexes for this grid and implement one of the two architectural patterns below.

## Solution 1: The Atlas Search Approach (Recommended)

Since you already pay for Atlas, you can use Atlas Search ($search) instead of standard queries (.find()). Atlas Search runs on Apache Lucene, which handles dynamic sorting and offset pagination across millions of documents natively, without needing compound database indexes.

## How to configure it:

   1. Create a single Atlas Search Index on your collection.
   2. Map customerId as a token or string type, and map your 10 grid fields as types that support sorting (like date, number, or token).
   3. Query using the aggregation pipeline:

```
db.collection.aggregate([
  {
    $search: {
      index: "your_grid_search_index",
      compound: {
        filter: [{
          text: { query: "CUSTOMER_ID_HERE", path: "customerId" }
        }]
      },
      // Lucene handles this sort effortlessly without 32MB database RAM limits
      sort: { "status": 1 } 
    }
  },
  { $skip: 200 },
  { $limit: 20 }
])
```

* Pros: Completely eliminates the 32 MB RAM crash. No index bloat. One index handles all 10 sort columns.
* Cons: Requires rewriting the grid's query code to use the aggregation framework.


## Solution 2: The B-Tree Index Compromise (If you cannot use Atlas Search)

If you are strictly forbidden from using Atlas Search and must use standard .find() queries, you cannot use the "Catch-All" index strategy. You must explicitly build compound indexes for the columns users actually sort by.

To prevent index bloat from 10 different columns, you must restrict the UI:

   1. Limit sorting to the 3-4 most critical columns (e.g., Status, Created Date, Modified Date).
   2. Build dedicated indexes for only those columns:
```   
   db.collection.createIndex({ customerId: 1, createdAt: -1 })
   db.collection.createIndex({ customerId: 1, status: 1 })
```
   3. Disable sorting on the other 6 columns in the UI, or force an explicit warning to the product team that those columns cannot be supported for Mega-Customers.

## The .skip() Danger Warning

Even with the correct compound index, .skip() gets progressively slower the further a user clicks into the pages (e.g., page 500). MongoDB still has to scan through all the index keys up to that offset point. If you stick with standard indexes, try to cap the maximum number of pages a user can click through (e.g., max 50 pages).
