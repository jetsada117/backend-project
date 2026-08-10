import numpy as np
from app.services.cosine_similarity_service import scorer

def test_similarity_identical_vectors():
    # 26 is the total length of the vector based on group_sizes: [6, 2, 3, 3, 4, 4, 4]
    vec = [0] * 26
    vec[0] = 1 # Age 0-6
    vec[6] = 1 # Gender Female
    
    score = scorer.calculate_similarity(vec, vec)
    assert score == 1.0

def test_similarity_different_vectors():
    vec_a = [0] * 26
    vec_a[0] = 1
    
    vec_b = [0] * 26
    vec_b[1] = 1 # Different age
    
    score = scorer.calculate_similarity(vec_a, vec_b)
    assert score < 1.0

def test_similarity_gender_weight():
    # Gender has weight 0.40, Age has 0.15
    # If gender matches but age doesn't, score should be higher than vice versa
    base = [0] * 26
    base[0] = 1 # Age
    base[6] = 1 # Gender
    
    # Match age only
    age_match = [0] * 26
    age_match[0] = 1
    age_match[7] = 1 # Different gender
    
    # Match gender only
    gender_match = [0] * 26
    gender_match[1] = 1 # Different age
    gender_match[6] = 1
    
    score_age = scorer.calculate_similarity(base, age_match)
    score_gender = scorer.calculate_similarity(base, gender_match)
    
    # Since gender has higher weight, gender_match should have higher similarity?
    # Actually, the dynamic_w logic might affect this. 
    # But generally, higher weight features impact the score more.
    assert score_gender > score_age
