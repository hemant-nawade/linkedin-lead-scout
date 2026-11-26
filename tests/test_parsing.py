from app import parsing as p

def test_keyword_intent_type():
    t = "We are looking for affiliate marketing partners and publishers. CPA, CPL. GEO: India. mail a@b.com"
    a = p.analyze(t, keywords=p.DEFAULT_KEYWORDS, intent_words=p.DEFAULT_INTENT_WORDS)
    assert a["keywords"] == ["affiliate marketing"]
    assert a["intent"] == "High"
    assert "Partner/publisher chahiye" in a["lead_types"]
    assert a["campaign_models"] == ["CPA", "CPL"]
    assert a["geo"] == "India"
    assert a["contacts"]["emails"] == ["a@b.com"]

def test_url_normalisation_dedupes_formats():
    a = p.normalize_post_url("https://www.linkedin.com/posts/x_y-activity-7262123456789012480-abCd?utm_source=share")
    b = p.normalize_post_url("linkedin.com/feed/update/urn:li:activity:7262123456789012480")
    assert a == b

def test_compliance_and_age():
    assert p.detect_compliance("iGaming CPA with USDT payouts")
    assert p.human_age(p.parse_age("5d")) == "5d"
    assert p.human_age(None) == "Date unknown"
