import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import taxonomy as tx  # noqa: E402


def label(text):
    df = pd.DataFrame({"project_title": [""], "abstract_text": [text]})
    return tx.label_projects(df).iloc[0]


def test_taxonomy_files_are_consistent():
    cats = set(tx.load_categories().category_id)
    terms = pd.read_csv(tx.TAXONOMY_DIR / "terms.csv")
    assert set(terms.category_id) <= cats
    assert set(terms.strength) <= {"strong", "weak"}
    assert set(terms.match_type) <= {"phrase", "acronym"}


def test_strong_term_assigns_category():
    r = label("We will train a convolutional neural network to segment tumors on MRI.")
    assert "deep_learning" in r.categories
    assert "medical_imaging" in r.categories
    assert r.ai_related


def test_single_weak_term_is_not_enough():
    r = label("Patients were assigned by classification of disease stage.")
    assert "machine_learning" not in r.categories


def test_two_weak_terms_assign_category():
    r = label("A classifier with cross-validation will be compared to clinicians.")
    assert "machine_learning" in r.categories


def test_ai_american_indian_alaska_native_excluded():
    r = label("This study enrolls AI/AN communities to reduce diabetes risk.")
    assert not r.ai_related


def test_neural_network_is_not_neuroscience():
    r = label("A neural network predicts readmission from electronic health records.")
    assert "neuroscience" not in r.categories
    assert "clinical_care" in r.categories


def test_application_area_needs_data_science():
    r = label("A randomized trial of exercise for depression in older adults.")
    assert r.categories == []


def test_llm_and_hyphen_variants():
    r = label("We fine tune a large-language model on clinical notes.")
    assert "generative_ai" in r.categories


def test_gpt_liver_enzyme_excluded():
    r = label("Serum GPT (glutamic pyruvic transaminase) levels were measured.")
    assert "generative_ai" not in r.categories


def test_data_science_without_ai():
    r = label("We build an agent-based model and a network analysis of clinic referrals.")
    assert "computational_modeling" in r.categories
    assert "network_analysis" in r.categories
    assert r.data_science_related
    assert not r.ai_related


def test_routine_statistics_not_flagged():
    r = label("Groups were compared with a t-test and logistic regression; p-values are reported.")
    assert not r.data_science_related


def test_lymph_nodes_not_network_analysis():
    r = label("Tumor cells spread to lymph nodes through a network of vessels.")
    assert "network_analysis" not in r.categories


def test_microscopy_visualization_not_data_visualization():
    r = label("Confocal microscopy will visualize mitochondria; visualization uses fluorescent dyes.")
    assert "data_visualization" not in r.categories
