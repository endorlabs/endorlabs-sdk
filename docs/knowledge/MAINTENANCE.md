# Knowledge Base Maintenance Guide

> **Maintaining the freshness and accuracy of the Endor Cockpit knowledge base**

## Overview

The Endor Cockpit knowledge base is a **portable shared learning index** that contains comprehensive documentation, API patterns, best practices, and operational procedures. This guide explains how to maintain its accuracy and freshness.

## When to Update the Knowledge Base

### Contradictions Found
- **API Behavior**: When actual API behavior differs from documented patterns
- **Error Messages**: When error messages or responses don't match documentation
- **Workflows**: When established procedures no longer work as documented
- **Security**: When security requirements or compliance standards change

### New Discoveries
- **Best Practices**: When better patterns are discovered through experience
- **Workarounds**: When solutions to common problems are found
- **Optimizations**: When more efficient approaches are identified
- **Integration Patterns**: When new integration methods are developed

### System Changes
- **API Updates**: When Endor Labs API changes or new endpoints are added
- **Dependencies**: When dependency versions or requirements change
- **Tools**: When development tools or processes are updated
- **Infrastructure**: When deployment or operational procedures change

## How to Identify Contradictions

### During Development
1. **Query First**: Always start by querying the knowledge base
2. **Compare Results**: Check if the retrieved information matches reality
3. **Test Assumptions**: Verify that documented patterns actually work
4. **Note Discrepancies**: Document any differences found

### During Operations
1. **Monitor Outcomes**: Track whether documented procedures succeed
2. **Error Analysis**: Analyze failures against documented troubleshooting
3. **Performance**: Note when documented optimizations don't work
4. **User Feedback**: Collect feedback on documentation accuracy

### During Testing
1. **Integration Tests**: Check if tests pass with documented patterns
2. **Edge Cases**: Verify documented workarounds for edge cases
3. **Error Handling**: Test documented error recovery procedures
4. **Security**: Validate documented security practices

## Process for Incorporating New Learnings

### 1. Document the Finding
Create a clear record of:
- **What was expected** (from knowledge base)
- **What actually happened** (reality)
- **The correct information** (new learning)
- **Context and conditions** (when this applies)

### 2. Update Documentation
Modify the relevant documentation files:
- **API Documentation**: Update `docs/SPECIFICATION.md`
- **Patterns**: Update persona-specific guides
- **Troubleshooting**: Update operational guides
- **Examples**: Update code examples and workflows

### 3. Rebuild the Knowledge Base
```bash
# Rebuild the vector database with updated content
uv run python workflow/init_vector_db.py --rebuild
```

### 4. Verify the Update
```python
# Test that the new information is properly indexed
from endor_cockpit.rag import query_vector_db

# Query for the updated information
results = query_vector_db("your specific question")
assert len(results["results"]) > 0
assert "updated content" in results["results"][0]["content"]
```

### 5. Test Integration
- Run relevant tests to ensure the update works
- Verify that the new information is accessible
- Check that related documentation is consistent

## Testing Knowledge Base Updates

### Automated Testing
```python
def test_knowledge_base_accuracy():
    """Test that knowledge base contains accurate information."""
    from endor_cockpit.rag import query_vector_db
    
    # Test specific queries that should return known results
    test_cases = [
        ("How do I create a namespace?", "canonical naming"),
        ("What are the API quirks?", "parent_namespace"),
        ("Security scanning", "endorctl scan"),
    ]
    
    for query, expected_content in test_cases:
        results = query_vector_db(query)
        assert len(results["results"]) > 0
        assert any(expected_content in result["content"] 
                  for result in results["results"])
```

### Manual Verification
1. **Query the Updated Topic**: Search for the specific information
2. **Check Relevance**: Verify results are relevant and accurate
3. **Test Edge Cases**: Query related topics to ensure consistency
4. **Validate Examples**: Ensure code examples work as documented

## Version Control Best Practices

### Documentation Changes
- **Commit Messages**: Use clear, descriptive commit messages
- **Atomic Changes**: Make focused changes to specific topics
- **Review Process**: Have changes reviewed by team members
- **Testing**: Test changes before committing

### Knowledge Base Rebuilds
- **Incremental Updates**: Use incremental updates when possible
- **Full Rebuilds**: Use `--rebuild` flag for major changes
- **Verification**: Always verify rebuilds with test queries
- **Documentation**: Document significant changes in commit messages

### Maintenance Schedule
- **Regular Reviews**: Schedule periodic reviews of knowledge base accuracy
- **After Updates**: Rebuild after any significant documentation changes
- **Before Releases**: Verify knowledge base before major releases
- **Post-Incidents**: Update after resolving operational issues

## Quality Assurance

### Content Quality
- **Accuracy**: Ensure all information is factually correct
- **Completeness**: Verify that all necessary information is included
- **Consistency**: Check that information is consistent across documents
- **Clarity**: Ensure information is clear and understandable

### Technical Quality
- **Indexing**: Verify that all content is properly indexed
- **Retrieval**: Test that queries return relevant results
- **Performance**: Ensure queries are fast and efficient
- **Reliability**: Verify that the system works consistently

## Monitoring and Metrics

### Usage Metrics
- **Query Frequency**: Track how often the knowledge base is queried
- **Query Success**: Monitor successful vs failed queries
- **Popular Topics**: Identify frequently accessed information
- **Gaps**: Identify topics that return no results

### Accuracy Metrics
- **Contradiction Reports**: Track reported contradictions
- **Update Frequency**: Monitor how often updates are needed
- **User Feedback**: Collect feedback on knowledge base usefulness
- **Success Rate**: Measure success of documented procedures

## Best Practices

### For AI Agents
1. **Always Query First**: Start every task by querying the knowledge base
2. **Verify Information**: Cross-check retrieved information with reality
3. **Report Contradictions**: Document any discrepancies found
4. **Update When Needed**: Incorporate new learnings into the knowledge base

### For Developers
1. **Document Changes**: Update documentation when making code changes
2. **Test Documentation**: Verify that documented procedures work
3. **Share Learnings**: Contribute new patterns and best practices
4. **Maintain Accuracy**: Keep documentation current and accurate

### For Operations
1. **Monitor Effectiveness**: Track whether documented procedures work
2. **Collect Feedback**: Gather input on documentation usefulness
3. **Update Procedures**: Modify documentation when processes change
4. **Share Knowledge**: Contribute operational insights to the knowledge base

## Conclusion

The knowledge base is a living system that requires active maintenance to remain valuable. By following these practices, we ensure that the Endor Cockpit knowledge base remains accurate, comprehensive, and useful for all AI agents and developers working with the system.

Remember: **Query First, Verify Always, Update When Needed**
