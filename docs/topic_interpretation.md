#  **TOPIC INTERPRETATION GUIDE - From Numbers to Stories**

##  **What Each Topic Number Actually Means**

Based on our LDA analysis of 1,796 reviews, here's what each topic represents:

### **Topic 0 (296 reviews, 16.5%): "Bleach Fan Debates"**

- **Sample text**: "When talking about BLEACH there's always a heated debate going on..."
- **Theme**: Bleach-specific discussions, fan debates, series controversies
- **Entity focus**: Bleach (186), Naruto (92), One Piece (18)
- **Story angle**: "Bleach fans are the most passionate and divisive"

### **Topic 1 (131 reviews, 7.3%): "One Piece Enthusiasm"**

- **Entity focus**: Bleach (73), One Piece (40), Naruto (18)
- **Theme**: One Piece-specific discussions, world-building, adventure
- **Story angle**: "One Piece fans focus on the journey and world-building"

### **Topic 2 (59 reviews, 3.3%): "Niche Criticisms"**

- **Theme**: Specialized criticisms, unique perspectives
- **Story angle**: "A small but vocal minority with specific critiques"

### **Topic 3 (531 reviews, 29.6%): "Universal Shonen Themes"**

- **Theme**: Common themes across all anime (character development, action, story)
- **Entity focus**: One Piece (424), Bleach (71), Naruto (36)
- **Story angle**: "The Big Three share common shonen DNA - this is what unites fans"

### **Topic 4 (66 reviews, 3.7%): "Bleach Character Focus"**

- **Entity focus**: One Piece (22), Bleach (31), Naruto (13)
- **Theme**: Character discussions, power systems, Soul Society
- **Story angle**: "Bleach fans are obsessed with characters and power systems"

### **Topic 5 (434 reviews, 24.2%): "Cross-Series Comparisons"**

- **Theme**: Comparing the Big Three, ranking them
- **Entity focus**: Naruto (383), Bleach (27), One Piece (24)
- **Story angle**: "Fans love to debate which series is best"

### **Topic 6 (103 reviews, 5.7%): "Animation & Production Quality"**

- **Theme**: Visual quality, animation, production values
- **Entity focus**: Bleach (61), One Piece (32), Naruto (10)
- **Story angle**: "One Piece fans appreciate the visual craftsmanship"

### **Topic 7 (176 reviews, 9.8%): "Franchise Legacy & Impact"**

- **Theme**: Long-term impact, cultural significance, legacy
- **Entity focus**: Bleach (127), Naruto (35), One Piece (14)
- **Story angle**: "These series have left lasting cultural impact"

## 📊 **Sentiment Score Interpretation**

### **VADER Compound Scores:**

- **0.8 to 1.0**: Very Positive (fans love it!)
- **0.5 to 0.8**: Positive (generally liked)
- **0.2 to 0.5**: Slightly Positive (mixed feelings)
- **0.0 to 0.2**: Neutral (indifferent)
- **-0.2 to 0.0**: Slightly Negative (mild dislike)
- **-0.5 to -0.2**: Negative (disliked)
- **-1.0 to -0.5**: Very Negative (fans hate it!)

### **VADER Component Scores:**

- **vader_pos**: How positive the review is (0.0 to 1.0)
- **vader_neu**: How neutral the review is (0.0 to 1.0)
- **vader_neg**: How negative the review is (0.0 to 1.0)

## 🎨 **How to Interpret This in Tableau**

### **1. Topic Labels (Calculated Fields)**

```sql
-- Topic Labels
CASE [lda_topic_id]
WHEN 0 THEN "Bleach Fan Debates"
WHEN 1 THEN "One Piece Enthusiasm"
WHEN 2 THEN "Niche Criticisms"
WHEN 3 THEN "Universal Shonen Themes"
WHEN 4 THEN "Bleach Character Focus"
WHEN 5 THEN "Cross-Series Comparisons"
WHEN 6 THEN "Animation & Production"
WHEN 7 THEN "Franchise Legacy"
ELSE "Unknown Topic"
END
```

### **2. Sentiment Categories**

```sql
-- Sentiment Categories
CASE
WHEN [vader_compound] >= 0.8 THEN "Very Positive"
WHEN [vader_compound] >= 0.5 THEN "Positive"
WHEN [vader_compound] >= 0.2 THEN "Slightly Positive"
WHEN [vader_compound] >= 0.0 THEN "Neutral"
WHEN [vader_compound] >= -0.2 THEN "Slightly Negative"
WHEN [vader_compound] >= -0.5 THEN "Negative"
ELSE "Very Negative"
END
```


