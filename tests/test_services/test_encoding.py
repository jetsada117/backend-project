from app.services.encoding_service import encoder

def test_text_to_vector_basic():
    text = "ผู้ชาย วัยรุ่น ผมดำ"
    vector = encoder.text_to_vector(text)
    
    # Check if gender 'ชาย' is set (index 6, 7 in total feature names)
    # feature_names order: age_cats(6), gender_cats(2), ...
    # gender_categories = ["หญิง", "ชาย"]
    # So 'ชาย' should be index 6 + 1 = 7
    assert vector[7] == 1
    assert vector[6] == 0

def test_vector_to_text():
    # Create a vector for a young female with black hair
    vector = [0] * 25
    vector[2] = 1 # วัยรุ่น
    vector[6] = 1 # หญิง
    vector[10] = 1 # ผมดำ
    vector[11] = 1 # ผมตรง
    vector[13] = 1 # คิ้วหนา
    vector[17] = 1 # ผิวขาว
    
    text_list = encoder.vector_to_text(vector)
    assert "หญิง" in text_list
    assert "วัยรุ่น" in text_list
    assert "ผมดำ" in text_list

def test_parse_text_complex():
    text = "ผู้หญิง วัยรุ่น ผมตรง คิ้วหนา ผิวสองสี"
    parsed = encoder.parse_text(text)
    
    assert parsed["gender"] == "หญิง"
    assert parsed["age"] == "วัยรุ่น"
    assert "คิ้วหนา" in parsed["eyebrow"]
    assert parsed["skin"] == "ผิวสองสี"
