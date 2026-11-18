---
title: Customize Solr Search Correctly
impact: HIGH
impactDescription: ensures optimal search relevance and performance
tags: search, solr, indexing, relevance
---

## Customize Solr Search Correctly

**Impact: HIGH (ensures optimal search relevance and performance)**

Solr powers product search in ICM. Proper configuration of indexing, schema, and query parameters is essential for relevant results and fast response times.

**Incorrect (poor Solr configuration):**

```java
// Bad: Searching all fields without relevance tuning
public SearchResult search(String query) {
    SolrQuery solrQuery = new SolrQuery(query);
    solrQuery.set("defType", "edismax");
    solrQuery.set("qf", "*");  // Search all fields equally!
    return solrClient.query(solrQuery);
}

// Bad: Not handling special characters
public SearchResult search(String userInput) {
    SolrQuery query = new SolrQuery(userInput);  // Could break query!
    return solrClient.query(query);
}

// Bad: Full reindex for every change
public void updateProduct(ProductBO product) {
    productRepository.save(product);
    solrIndexer.reindexAll();  // Very slow!
}

// Bad: No query optimization
public SearchResult searchProducts(SearchRequest request) {
    SolrQuery query = new SolrQuery(request.getQuery());
    query.setRows(10000);  // Fetching way too many!
    query.setFields("*");  // Returning all fields!
    return solrClient.query(query);
}
```

**Correct (optimized Solr integration):**

```java
// Good: Properly configured query with field boosting
@Injectable
public class ProductSearchService {

    @Inject
    private SolrClient solrClient;

    public SearchResult search(SearchRequest request) {
        SolrQuery query = new SolrQuery();

        // Use eDisMax for relevance tuning
        query.set("defType", "edismax");

        // Escape and set query
        String escapedQuery = ClientUtils.escapeQueryChars(request.getQuery());
        query.setQuery(escapedQuery);

        // Field boosting for relevance
        query.set("qf", String.join(" ",
            "sku^10",           // Exact SKU match highest priority
            "name^5",           // Product name high priority
            "brand^3",          // Brand moderate priority
            "description^1",    // Description low priority
            "attributes^0.5"    // Attributes lowest priority
        ));

        // Phrase boosting for multi-word queries
        query.set("pf", "name^10 description^2");
        query.set("ps", "2");  // Phrase slop

        // Minimum match
        query.set("mm", "75%");

        // Pagination
        query.setStart(request.getPage() * request.getPageSize());
        query.setRows(request.getPageSize());

        // Return only needed fields
        query.setFields("id", "sku", "name", "price", "thumbnailUrl", "score");

        return executeQuery(query);
    }
}

// Good: Incremental indexing
@Injectable
public class ProductIndexingService {

    @Inject
    private SolrClient solrClient;

    @Inject
    private ProductIndexMapper indexMapper;

    public void indexProduct(ProductBO product) {
        SolrInputDocument doc = indexMapper.toSolrDocument(product);
        solrClient.add(doc);
        // Soft commit for near real-time visibility
        solrClient.commit(false, false, true);
    }

    public void indexProducts(List<ProductBO> products) {
        List<SolrInputDocument> docs = products.stream()
            .map(indexMapper::toSolrDocument)
            .collect(toList());

        solrClient.add(docs);
        solrClient.commit();
    }

    public void deleteProduct(String productId) {
        solrClient.deleteById(productId);
        solrClient.commit();
    }

    // Atomic update for partial changes
    public void updatePrice(String productId, Money newPrice) {
        SolrInputDocument doc = new SolrInputDocument();
        doc.setField("id", productId);

        Map<String, Object> priceUpdate = new HashMap<>();
        priceUpdate.put("set", newPrice.getAmount().toString());
        doc.setField("price", priceUpdate);

        solrClient.add(doc);
        solrClient.commit();
    }
}

// Good: Custom field types in schema
/*
<fieldType name="text_product" class="solr.TextField">
    <analyzer type="index">
        <tokenizer class="solr.StandardTokenizerFactory"/>
        <filter class="solr.LowerCaseFilterFactory"/>
        <filter class="solr.StopFilterFactory" words="stopwords.txt"/>
        <filter class="solr.SynonymGraphFilterFactory" synonyms="synonyms.txt"/>
        <filter class="solr.FlattenGraphFilterFactory"/>
        <filter class="solr.EdgeNGramFilterFactory" minGramSize="2" maxGramSize="15"/>
    </analyzer>
    <analyzer type="query">
        <tokenizer class="solr.StandardTokenizerFactory"/>
        <filter class="solr.LowerCaseFilterFactory"/>
        <filter class="solr.StopFilterFactory" words="stopwords.txt"/>
        <filter class="solr.SynonymGraphFilterFactory" synonyms="synonyms.txt"/>
    </analyzer>
</fieldType>
*/

// Good: Faceted search
@Injectable
public class FacetedSearchService {

    public SearchResult searchWithFacets(SearchRequest request) {
        SolrQuery query = buildBaseQuery(request);

        // Enable faceting
        query.setFacet(true);
        query.setFacetMinCount(1);
        query.setFacetLimit(50);

        // Add facet fields
        query.addFacetField("category");
        query.addFacetField("brand");
        query.addFacetField("color");

        // Range facet for price
        query.addNumericRangeFacet("price", 0, 1000, 100);

        // Apply selected facets as filters
        if (request.getFilters() != null) {
            for (FacetFilter filter : request.getFilters()) {
                query.addFilterQuery(
                    filter.getField() + ":" +
                    ClientUtils.escapeQueryChars(filter.getValue())
                );
            }
        }

        return executeQuery(query);
    }
}

// Good: Search suggestions/autocomplete
@Injectable
public class SearchSuggestionService {

    public List<String> suggest(String prefix, int limit) {
        SolrQuery query = new SolrQuery();
        query.setRequestHandler("/suggest");
        query.set("suggest.q", prefix);
        query.set("suggest.count", limit);
        query.set("suggest.dictionary", "productSuggester");

        QueryResponse response = solrClient.query(query);
        SuggesterResponse suggestions = response.getSuggesterResponse();

        return suggestions.getSuggestions().get("productSuggester")
            .stream()
            .map(Suggestion::getTerm)
            .collect(toList());
    }
}

// Good: Spell checking
@Injectable
public class SpellCheckService {

    public SearchResult searchWithSpellCheck(String query) {
        SolrQuery solrQuery = buildBaseQuery(query);

        // Enable spell checking
        solrQuery.set("spellcheck", "true");
        solrQuery.set("spellcheck.q", query);
        solrQuery.set("spellcheck.count", 5);
        solrQuery.set("spellcheck.collate", true);
        solrQuery.set("spellcheck.maxCollations", 3);

        QueryResponse response = solrClient.query(solrQuery);
        SpellCheckResponse spellCheck = response.getSpellCheckResponse();

        SearchResult result = mapResponse(response);

        if (spellCheck != null && !spellCheck.getCollatedResults().isEmpty()) {
            result.setSpellCheckSuggestion(
                spellCheck.getCollatedResults().get(0).getCollationQueryString()
            );
        }

        return result;
    }
}
```

**Solr configuration best practices:**

| Setting | Development | Production |
|---------|-------------|------------|
| autoCommit maxTime | 15000ms | 60000ms |
| autoSoftCommit maxTime | 1000ms | 5000ms |
| ramBufferSizeMB | 100 | 256+ |
| maxWarmingSearchers | 2 | 4 |

Reference: [ICM Search Customization](https://knowledge.intershop.com/kb/index.php/Display/2X2890)
