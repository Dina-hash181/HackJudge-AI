import json
from typing import Dict, Any, List

def detect_project_domain(project: Dict[str, Any]) -> str:
    """Classifies a project into its core technology domain."""
    track = (project.get("track_name") or "").lower()
    title = (project.get("title") or "").lower()
    summary = (project.get("summary") or "").lower()

    # 1. Primary classification by Track Name
    if any(k in track for k in ["security", "crypto", "privacy"]):
        return "security"
    elif any(k in track for k in ["developer", "tools", "infra", "devtools"]):
        return "devtools"
    elif any(k in track for k in ["data", "analytic", "ai", "machine learning"]):
        return "analytics"
    elif any(k in track for k in ["accessib", "a11y"]):
        return "accessibility"
    elif any(k in track for k in ["health", "bio", "medical", "telemetry"]):
        return "health"
    elif any(k in track for k in ["educat", "learning", "edtech"]):
        return "education"
    elif any(k in track for k in ["climate", "sustain", "green", "energy"]):
        return "climate"
    elif any(k in track for k in ["hardware", "iot", "embedded", "robotics"]):
        return "hardware"

    # 2. Secondary fallback by Title/Summary keywords
    if any(k in title for k in ["signal", "beacon", "drift", "vault"]):
        return "security"
    elif any(k in title for k in ["compass", "switch"]):
        return "devtools"
    elif any(k in title for k in ["meadow", "harbour"]):
        return "accessibility"
    elif any(k in title for k in ["pulse", "hollow"]):
        return "health"
    elif any(k in title for k in ["solar", "eco"]):
        return "climate"

    return "devtools"

def get_project_repo_files(project: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates domain-tailored, multi-file code repositories for evaluators,
    with distinct architectures, source files, and unit tests per category.
    """
    pid = project.get("id", "prj_01")
    title = project.get("title", f"Project {pid}")
    summary = project.get("summary", "Autonomous hackathon module.")
    track = project.get("track_name", "General")
    team = project.get("team_name", "Developers")
    problem = project.get("problem_statement", "Addressing core domain bottlenecks.")
    clean_slug = title.lower().replace(" ", "_")
    domain = detect_project_domain(project)

    files = {}

    if domain == "security":
        files = {
            "README.md": f"""# 🛡️ {title} - Cryptographic Zero-Knowledge Vault
> **Track**: {track} | **Team**: {team}  
> *{summary}*

## Threat Model & Security Posture
{problem}

## Core Architecture
- **Cryptographic Primitives**: Constant-time AES-256-GCM authenticated cipher with SHA3-512 integrity digests.
- **Key Derivation**: Argon2id memory-hard hashing with dynamic salt rotation.
- **Zero-Knowledge Proofs**: Groth16 zk-SNARK verifier ensuring data attestation without revealing plaintext payloads.
- **Intrusion Shield**: Heuristic entropy analysis detecting timing side-channels, SQLi, and replay attacks.

## Local Execution
```bash
git clone https://github.com/dogfood2026/{clean_slug}.git
cd {clean_slug}
pip install -r requirements.txt
python src/main.py
```
""",
            "src/crypto_vault.py": f'''"""
Cryptographic Vault & Key Isolation Engine for {title}.
Constant-time cryptographic operations with hardware entropy seeding.
"""
import os
import hashlib
import hmac
import secrets
from typing import Dict, Any, Tuple

class CryptoVault:
    def __init__(self, key_bytes: int = 32):
        self.master_key = secrets.token_bytes(key_bytes)
        self.revocation_ledger = set()
        self.entropy_pool_bits = 4096

    def seal_payload(self, plaintext: str, context: str = "DEFAULT") -> Dict[str, str]:
        """Encrypts and binds payload with authenticated HMAC-SHA256 signature."""
        salt = secrets.token_bytes(16)
        derived_key = hashlib.pbkdf2_hmac("sha256", self.master_key, salt, 200_000)
        
        # Emulated authenticated stream cipher
        nonce = secrets.token_bytes(12)
        raw_bytes = plaintext.encode("utf-8")
        cipher_bytes = bytes([b ^ derived_key[i % len(derived_key)] for i, b in enumerate(raw_bytes)])
        
        signature = hmac.new(derived_key, cipher_bytes + salt + nonce, hashlib.sha256).hexdigest()
        
        return {{
            "ciphertext": cipher_bytes.hex(),
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "signature": signature,
            "context": context,
            "algorithm": "AES-256-GCM-SIMULATED"
        }}

    def verify_and_unseal(self, envelope: Dict[str, str]) -> Tuple[bool, str]:
        """Verifies signature authenticity and unseals payload without side channels."""
        salt = bytes.fromhex(envelope["salt"])
        nonce = bytes.fromhex(envelope["nonce"])
        cipher_bytes = bytes.fromhex(envelope["ciphertext"])
        
        derived_key = hashlib.pbkdf2_hmac("sha256", self.master_key, salt, 200_000)
        expected_sig = hmac.new(derived_key, cipher_bytes + salt + nonce, hashlib.sha256).hexdigest()
        
        if not secrets.compare_digest(expected_sig, envelope["signature"]):
            return False, "SIGNATURE_VERIFICATION_FAILED"
            
        plain_bytes = bytes([b ^ derived_key[i % len(derived_key)] for i, b in enumerate(cipher_bytes)])
        return True, plain_bytes.decode("utf-8")
''',
            "src/threat_detector.py": f'''"""
Real-Time Threat Detection & Heuristic Traffic Anomaly Analyzer.
"""
import re
from typing import Dict, Any

class ThreatDetector:
    SUSPICIOUS_PATTERNS = [
        re.compile(r"(--|;|union|select|insert|drop)", re.IGNORECASE),
        re.compile(r"(<script|javascript:|onerror=)", re.IGNORECASE),
        re.compile(r"(\.\./\.\./|etc/passwd)", re.IGNORECASE)
    ]

    def analyze_payload(self, raw_input: str) -> Dict[str, Any]:
        """Inspects incoming payloads for injection vectors and entropy anomalies."""
        threat_score = 0
        detected_anomalies = []

        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.search(raw_input):
                threat_score += 45
                detected_anomalies.append(f"INJECTION_SIGNATURE_MATCH: {{pattern.pattern}}")

        if len(raw_input) > 2048:
            threat_score += 20
            detected_anomalies.append("PAYLOAD_LENGTH_OVERFLOW_SUSPECT")

        return {{
            "is_malicious": threat_score >= 40,
            "threat_score": min(threat_score, 100),
            "threat_level": "CRITICAL" if threat_score >= 80 else ("HIGH" if threat_score >= 40 else "CLEAN"),
            "anomalies": detected_anomalies
        }}
''',
            "src/main.py": f'''#!/usr/bin/env python3
"""
Main Security Microservice Entry for {title}.
"""
import logging
from src.crypto_vault import CryptoVault
from src.threat_detector import ThreatDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("{clean_slug}")

def main():
    logger.info("Initializing {title} Secure Runtime...")
    vault = CryptoVault()
    detector = ThreatDetector()

    # Self-test encryption
    test_data = "AUTHENTICATED_HEALTH_BEACON_PAYLOAD"
    sealed = vault.seal_payload(test_data, "BOOT_VERIFY")
    valid, unsealed = vault.verify_and_unseal(sealed)
    
    assert valid and unsealed == test_data, "Cryptographic boot test failed"
    logger.info("Cryptographic engine verified. Zero-knowledge proof subsystem ONLINE.")

if __name__ == "__main__":
    main()
''',
            "tests/test_crypto.py": f'''import unittest
from src.crypto_vault import CryptoVault
from src.threat_detector import ThreatDetector

class Test{clean_slug.title().replace("_", "")}(unittest.TestCase):
    def setUp(self):
        self.vault = CryptoVault()
        self.detector = ThreatDetector()

    def test_encryption_roundtrip(self):
        secret = "super_confidential_token_9988"
        envelope = self.vault.seal_payload(secret)
        valid, decrypted = self.vault.verify_and_unseal(envelope)
        self.assertTrue(valid)
        self.assertEqual(decrypted, secret)

    def test_tamper_detection(self):
        envelope = self.vault.seal_payload("unaltered_data")
        # Tamper ciphertext
        tampered_cipher = envelope["ciphertext"][:-2] + "ff"
        envelope["ciphertext"] = tampered_cipher
        valid, _ = self.vault.verify_and_unseal(envelope)
        self.assertFalse(valid)

    def test_sqli_detection(self):
        result = self.detector.analyze_payload("admin' UNION SELECT password FROM users--")
        self.assertTrue(result["is_malicious"])
        self.assertEqual(result["threat_level"], "HIGH")

if __name__ == "__main__":
    unittest.main()
''',
            "security.config.json": json.dumps({
                "app_name": title,
                "cipher_suite": "AES-256-GCM / SHA3-512",
                "key_rotation_interval_hours": 24,
                "max_auth_attempts": 5,
                "enforce_zero_knowledge_proofs": True,
                "anti_replay_window_sec": 30
            }, indent=2)
        }

    elif domain == "devtools":
        files = {
            "README.md": f"""# ⚡ {title} - High-Performance Developer CLI & AST Tooling
> **Track**: {track} | **Team**: {team}  
> *{summary}*

## Problem Statement
{problem}

## Capabilities & Architecture
- **AST Parser & Optimizer**: Traverses abstract syntax trees to eliminate dead code and fold constant expressions.
- **Sub-Millisecond Benchmark Suite**: Microsecond-precision benchmarking measuring JIT throughput and branch prediction.
- **Zero-Dependency CLI**: Self-contained runtime executable across Linux, macOS, and Windows.

## Quickstart
```bash
git clone https://github.com/dogfood2026/{clean_slug}.git
cd {clean_slug}
python src/cli.py --benchmark --iterations=10000
```
""",
            "src/ast_optimizer.py": f'''"""
AST Parser & Tree Optimization Engine for {title}.
Performs constant folding, dead branch pruning, and symbol flattening.
"""
import ast
import time
from typing import Dict, Any

class AstOptimizer:
    def __init__(self):
        self.transforms_applied = 0
        self.eliminated_dead_branches = 0

    def optimize_snippet(self, source_code: str) -> Dict[str, Any]:
        """Parses Python source, transforms nodes, and outputs optimized metrics."""
        start = time.perf_counter()
        tree = ast.parse(source_code)
        
        initial_node_count = len(list(ast.walk(tree)))
        
        # Simulated constant folding & simplification
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                self.transforms_applied += 1
            elif isinstance(node, ast.If):
                self.eliminated_dead_branches += 1

        elapsed_ms = (time.perf_counter() - start) * 1000
        
        return {{
            "original_nodes": initial_node_count,
            "optimized_nodes": max(1, initial_node_count - self.transforms_applied),
            "transforms_applied": self.transforms_applied,
            "dead_branches_pruned": self.eliminated_dead_branches,
            "parse_latency_ms": round(elapsed_ms, 3)
        }}
''',
            "src/benchmark.py": f'''"""
High-Throughput Micro-Benchmark Runner for {title}.
"""
import time
from typing import Callable, Dict, Any

class BenchmarkSuite:
    def __init__(self):
        self.results = []

    def run_benchmark(self, name: str, iterations: int = 10_000) -> Dict[str, Any]:
        """Executes tight loop timing to evaluate ops/sec and instruction throughput."""
        start = time.perf_counter()
        
        # Workload: arithmetic pipeline with accumulator
        acc = 0
        for i in range(iterations):
            acc += (i ^ 0x55) & 0xFF
            
        elapsed = time.perf_counter() - start
        ops_per_sec = int(iterations / elapsed) if elapsed > 0 else 999_999_999

        res = {{
            "name": name,
            "iterations": iterations,
            "elapsed_sec": round(elapsed, 4),
            "ops_per_second": f"{{ops_per_sec:,}} ops/sec",
            "p99_latency_us": round((elapsed / iterations) * 1_000_000, 2)
        }}
        self.results.append(res)
        return res
''',
            "src/cli.py": f'''#!/usr/bin/env python3
"""
CLI Tool Entry Point for {title}.
"""
import sys
import logging
from src.ast_optimizer import AstOptimizer
from src.benchmark.py import BenchmarkSuite if False else None
from src.benchmark import BenchmarkSuite

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("{clean_slug}")

def main():
    logger.info("⚡ {title} DevTools CLI v2.4.0")
    optimizer = AstOptimizer()
    sample = """
def compute_metrics(x, y):
    val = 10 + 20
    if False:
        print("dead code")
    return x * val + y
    """
    res = optimizer.optimize_snippet(sample)
    logger.info(f"AST Analysis complete in {{res['parse_latency_ms']}}ms (Nodes: {{res['optimized_nodes']}})")
    
    suite = BenchmarkSuite()
    bench = suite.run_benchmark("JIT_SYNTAX_PARSE", 50_000)
    logger.info(f"Benchmark: {{bench['ops_per_second']}} (P99: {{bench['p99_latency_us']}} µs)")

if __name__ == "__main__":
    main()
''',
            "tests/test_cli.py": f'''import unittest
from src.ast_optimizer import AstOptimizer
from src.benchmark import BenchmarkSuite

class Test{clean_slug.title().replace("_", "")}(unittest.TestCase):
    def test_optimizer(self):
        opt = AstOptimizer()
        res = opt.optimize_snippet("x = 5 + 5\\nif True:\\n    print(x)")
        self.assertGreater(res["original_nodes"], 0)
        self.assertLess(res["parse_latency_ms"], 50.0)

    def test_benchmark_runner(self):
        suite = BenchmarkSuite()
        bench = suite.run_benchmark("FAST_LOOP", 1000)
        self.assertGreater(bench["iterations"], 0)

if __name__ == "__main__":
    unittest.main()
''',
            "pyproject.toml": f"""[project]
name = "{clean_slug}"
version = "2.4.0"
description = "{summary}"
authors = [{{ name = "{team}" }}]
dependencies = []
requires-python = ">=3.10"

[project.scripts]
{clean_slug} = "src.cli:main"
"""
        }

    elif domain == "analytics":
        files = {
            "README.md": f"""# 📊 {title} - Real-Time Stream Analytics & Vector Embeddings
> **Track**: {track} | **Team**: {team}  
> *{summary}*

## Architecture Overview
- **Stream Ingestion Engine**: Micro-batched windowing engine with sub-3ms latency SLA.
- **Vector Cosine Similarity**: In-memory dense matrix indexing for real-time semantic discovery.
- **Statistical Anomaly Scorer**: Z-score and Isolation Forest heuristics for real-time drift detection.
""",
            "src/pipeline.py": f'''"""
Stream Ingestion & Feature Windowing Pipeline for {title}.
"""
import time
import math
from typing import List, Dict, Any

class StreamPipeline:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.buffer: List[float] = []

    def ingest_metric(self, value: float) -> Dict[str, Any]:
        """Ingests a telemetry point into the sliding window and calculates rolling statistics."""
        self.buffer.append(value)
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)

        n = len(self.buffer)
        mean = sum(self.buffer) / n
        variance = sum((x - mean) ** 2 for x in self.buffer) / n if n > 1 else 0.0
        std_dev = math.sqrt(variance)

        # Anomaly detection via Z-score
        z_score = abs(value - mean) / (std_dev if std_dev > 0.001 else 1.0)
        is_anomaly = z_score > 2.5

        return {{
            "window_count": n,
            "rolling_mean": round(mean, 3),
            "std_dev": round(std_dev, 3),
            "z_score": round(z_score, 2),
            "is_anomaly": is_anomaly,
            "timestamp": time.time()
        }}
''',
            "src/vector_search.py": f'''"""
Dense Vector Indexing & Approximate Cosine Search.
"""
import math
from typing import List, Tuple

class VectorIndex:
    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        self.index: List[Tuple[str, List[float]]] = []

    def add_vector(self, doc_id: str, vector: List[float]):
        self.index.append((doc_id, vector))

    def search_nearest(self, query: List[float], top_k: int = 3) -> List[Tuple[str, float]]:
        scores = []
        for doc_id, vec in self.index:
            dot = sum(a * b for a, b in zip(query, vec))
            norm_a = math.sqrt(sum(a * a for a in query)) or 1.0
            norm_b = math.sqrt(sum(b * b for b in vec)) or 1.0
            sim = dot / (norm_a * norm_b)
            scores.append((doc_id, round(sim, 4)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
''',
            "src/main.py": f'''#!/usr/bin/env python3
"""
Analytics Pipeline Server for {title}.
"""
import logging
from src.pipeline import StreamPipeline
from src.vector_search import VectorIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("{clean_slug}")

def main():
    logger.info("Initializing {title} Stream Engine...")
    pipeline = StreamPipeline()
    v_index = VectorIndex()

    for i in range(10):
        pipeline.ingest_metric(100.0 + (i % 3) * 2.5)

    res = pipeline.ingest_metric(195.0) # Anomaly injection
    logger.info(f"Pipeline running. Rolling Mean: {{res['rolling_mean']}}, Anomaly Detected: {{res['is_anomaly']}}")

if __name__ == "__main__":
    main()
''',
            "tests/test_pipeline.py": f'''import unittest
from src.pipeline import StreamPipeline
from src.vector_search import VectorIndex

class TestAnalytics(unittest.TestCase):
    def test_rolling_anomaly(self):
        pipe = StreamPipeline(window_size=20)
        for _ in range(15):
            pipe.ingest_metric(50.0)
        res = pipe.ingest_metric(250.0)
        self.assertTrue(res["is_anomaly"])

    def test_vector_similarity(self):
        v = VectorIndex(4)
        v.add_vector("doc1", [1.0, 0.0, 0.0, 0.0])
        v.add_vector("doc2", [0.0, 1.0, 0.0, 0.0])
        match = v.search_nearest([0.9, 0.1, 0.0, 0.0], top_k=1)
        self.assertEqual(match[0][0], "doc1")

if __name__ == "__main__":
    unittest.main()
''',
            "requirements.txt": "numpy>=1.26.0\nscipy>=1.12.0\npydantic>=2.6.0\n"
        }

    elif domain == "accessibility":
        files = {
            "README.md": f"""# ♿ {title} - Inclusive Assistive Technology & WCAG AAA Engine
> **Track**: {track} | **Team**: {team}  
> *{summary}*

## Mission Statement
{problem}

## Core Features
- **WCAG 2.2 AAA Contrast Verification**: Evaluates APCA and WCAG contrast ratios in real time.
- **Multi-Modal Screen Reader Bridge**: Translates structural DOM elements into spoken phonemes and Braille dot matrix grids.
- **Cognitive Load Optimizer**: Reduces visual noise and generates dyslexia-friendly color adaptations.
""",
            "src/contrast_engine.py": f'''"""
WCAG 2.2 Color Contrast & APCA Perception Engine for {title}.
"""
import math
from typing import Tuple, Dict, Any

class ContrastEngine:
    @staticmethod
    def _srgb_to_luminance(r: int, g: int, b: int) -> float:
        """Converts 8-bit sRGB channels to relative luminance."""
        channels = []
        for c in (r, g, b):
            c_norm = c / 255.0
            if c_norm <= 0.03928:
                channels.append(c_norm / 12.92)
            else:
                channels.append(((c_norm + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    def calculate_ratio(self, fg_rgb: Tuple[int, int, int], bg_rgb: Tuple[int, int, int]) -> Dict[str, Any]:
        l1 = self._srgb_to_luminance(*fg_rgb)
        l2 = self._srgb_to_luminance(*bg_rgb)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        ratio = (lighter + 0.05) / (darker + 0.05)

        return {{
            "contrast_ratio": round(ratio, 2),
            "ratio_string": f"{{round(ratio, 2)}}:1",
            "passes_aa_normal": ratio >= 4.5,
            "passes_aa_large": ratio >= 3.0,
            "passes_aaa_normal": ratio >= 7.0,
            "rating": "AAA" if ratio >= 7.0 else ("AA" if ratio >= 4.5 else "FAIL")
        }}
''',
            "src/screen_reader.py": f'''"""
Speech & Tactile Haptic Synthesis Driver for {title}.
"""
from typing import Dict, Any, List

class ScreenReaderBridge:
    def __init__(self):
        self.phoneme_buffer: List[str] = []

    def synthesize_announcement(self, role: str, label: str, state: str = "") -> Dict[str, Any]:
        """Formats ARIA live-region announcements with polite voice priority."""
        text = f"{{role.capitalize()}}, {{label}}."
        if state:
            text += f" Current state: {{state}}."

        haptic_pattern = [80, 40, 80] if role == "button" else [40]

        return {{
            "spoken_audio_text": text,
            "estimated_speech_duration_ms": len(text) * 45,
            "haptic_pattern_ms": haptic_pattern,
            "aria_live": "polite"
        }}
''',
            "src/main.py": f'''#!/usr/bin/env python3
"""
Accessibility Server for {title}.
"""
import logging
from src.contrast_engine import ContrastEngine
from src.screen_reader import ScreenReaderBridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("{clean_slug}")

def main():
    logger.info("Initializing {title} Assistive System...")
    engine = ContrastEngine()
    reader = ScreenReaderBridge()

    # Dark teal text on white background test
    result = engine.calculate_ratio((15, 118, 110), (255, 255, 255))
    logger.info(f"WCAG Verification: {{result['ratio_string']}} -> Rating: {{result['rating']}}")

    ann = reader.synthesize_announcement("button", "Submit Project", "Enabled")
    logger.info(f"Synthesized Speech: '{{ann['spoken_audio_text']}}'")

if __name__ == "__main__":
    main()
''',
            "tests/test_a11y.py": f'''import unittest
from src.contrast_engine import ContrastEngine
from src.screen_reader import ScreenReaderBridge

class TestAccessibility(unittest.TestCase):
    def test_high_contrast(self):
        engine = ContrastEngine()
        res = engine.calculate_ratio((0, 0, 0), (255, 255, 255))
        self.assertEqual(res["rating"], "AAA")
        self.assertGreaterEqual(res["contrast_ratio"], 20.0)

    def test_screen_reader_synthesis(self):
        bridge = ScreenReaderBridge()
        out = bridge.synthesize_announcement("link", "Explore Gallery")
        self.assertIn("Explore Gallery", out["spoken_audio_text"])

if __name__ == "__main__":
    unittest.main()
''',
            "package.json": json.dumps({
                "name": clean_slug,
                "version": "1.0.0",
                "description": summary,
                "main": "src/main.py",
                "scripts": { "test": "python -m unittest tests/test_a11y.py" }
            }, indent=2)
        }

    elif domain == "health":
        files = {
            "README.md": f"""# 🩺 {title} - Continuous Biometric Telemetry & Vital Alerting
> **Track**: {track} | **Team**: {team}  
> *{summary}*

## Clinical & Healthcare Objectives
{problem}

## System Architecture
- **ECG & Pulse Oximetry Stream**: Ingests real-time Photoplethysmogram (PPG) and electrocardiogram telemetry.
- **Arrhythmia Alert Classifier**: Evaluates QRS complex intervals and triggers sub-second emergency clinical alerts.
- **HIPAA-Compliant Encrypted Vault**: Zero-knowledge patient identifiability masking conforming to HL7 FHIR standards.
""",
            "src/vitals_telemetry.py": f'''"""
High-Frequency Vital Signs Telemetry Engine for {title}.
"""
import time
import math
from typing import Dict, Any

class VitalsMonitor:
    def __init__(self, resting_bpm: int = 72):
        self.resting_bpm = resting_bpm
        self.spo2_baseline = 98.5

    def sample_vitals(self, stress_factor: float = 0.0) -> Dict[str, Any]:
        """Produces verified cardiac telemetry and blood oxygenation saturation."""
        t = time.time()
        # Simulated sinus rhythm with respiratory sinus arrhythmia oscillation
        bpm = self.resting_bpm + math.sin(t / 2.0) * 4.0 + (stress_factor * 25.0)
        spo2 = max(88.0, self.spo2_baseline - (stress_factor * 6.0))
        
        # Clinical status evaluation
        status = "NORMAL_SINUS"
        is_critical = False
        if bpm > 110:
            status = "TACHYCARDIA_DETECTED"
            is_critical = True
        elif spo2 < 92.0:
            status = "HYPOXEMIA_WARNING"
            is_critical = True

        return {{
            "heart_rate_bpm": round(bpm, 1),
            "spo2_percent": round(spo2, 1),
            "status": status,
            "is_critical": is_critical,
            "perfusion_index": 4.8,
            "timestamp": t
        }}
''',
            "src/hipaa_vault.py": f'''"""
HIPAA Security Rule Vault & De-Identification Engine.
Masks Protected Health Information (PHI) while maintaining longitudinal research utility.
"""
import hashlib
from typing import Dict, Any

class HipaaVault:
    @staticmethod
    def pseudonymize_patient_record(patient_id: str, raw_vitals: Dict[str, Any]) -> Dict[str, Any]:
        """Generates cryptographically blinded record conforming to Safe Harbor method."""
        salt = "DOGFOOD_CLINICAL_SALT_2026"
        token = hashlib.sha256(f"{{patient_id}}_{{salt}}".encode()).hexdigest()[:16]

        return {{
            "pseudonym_id": f"PAT-{{token.upper()}}",
            "telemetry": raw_vitals,
            "encrypted": True,
            "audit_compliance": "HIPAA_SAFE_HARBOR_VERIFIED"
        }}
''',
            "src/main.py": f'''#!/usr/bin/env python3
"""
Health Telemetry Microservice for {title}.
"""
import logging
from src.vitals_telemetry import VitalsMonitor
from src.hipaa_vault import HipaaVault

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("{clean_slug}")

def main():
    logger.info("Initializing {title} Vital Signs Engine...")
    monitor = VitalsMonitor()
    reading = monitor.sample_vitals()
    logger.info(f"Vitals reading: {{reading['heart_rate_bpm']}} BPM, SpO2: {{reading['spo2_percent']}}% ({{reading['status']}})")

    anon = HipaaVault.pseudonymize_patient_record("PATIENT_7741", reading)
    logger.info(f"Encrypted Safe Harbor ID: {{anon['pseudonym_id']}}")

if __name__ == "__main__":
    main()
''',
            "tests/test_telemetry.py": f'''import unittest
from src.vitals_telemetry import VitalsMonitor
from src.hipaa_vault import HipaaVault

class TestHealth(unittest.TestCase):
    def test_vitals_sampling(self):
        monitor = VitalsMonitor(75)
        v = monitor.sample_vitals(stress_factor=0.0)
        self.assertGreater(v["heart_rate_bpm"], 60)
        self.assertGreater(v["spo2_percent"], 90)

    def test_critical_trigger(self):
        monitor = VitalsMonitor(75)
        v = monitor.sample_vitals(stress_factor=2.0)
        self.assertTrue(v["is_critical"])

if __name__ == "__main__":
    unittest.main()
''',
            "requirements.txt": "scipy>=1.12.0\ncryptography>=42.0.0\n"
        }

    elif domain == "education":
        files = {
            "README.md": f"""# 🎓 {title} - Adaptive Curriculum & Knowledge Graph Engine
> **Track**: {track} | **Team**: {team}  
> *{summary}*

## Pedagogical Objectives
{problem}

## Architecture
- **Knowledge Graph Navigator**: Directed acyclic graph mapping prerequisite concepts and mastery frontiers.
- **Item Response Theory (IRT)**: Calibrates question difficulty against real-time student aptitude.
- **Spaced Repetition Scheduler**: SuperMemo-2 heuristic maximizing retention intervals.
""",
            "src/adaptive_engine.py": f'''"""
Adaptive Question Generation & Aptitude Scoring for {title}.
"""
import math
from typing import Dict, Any, List

class AdaptiveLearningEngine:
    def __init__(self):
        self.mastery_scores: Dict[str, float] = {{
            "Variables & Types": 0.92,
            "Control Flow": 0.85,
            "Algorithms": 0.64,
            "System Architecture": 0.45
        }}

    def get_next_challenge(self) -> Dict[str, Any]:
        """Selects optimal concept node at the edge of the student's mastery frontier."""
        weakest_concept = min(self.mastery_scores.items(), key=lambda x: x[1])
        concept, score = weakest_concept

        return {{
            "target_concept": concept,
            "current_mastery": round(score * 100, 1),
            "challenge_prompt": f"Explain optimal partition handling in {{concept}}.",
            "difficulty_level": "INTERMEDIATE" if score > 0.5 else "FOUNDATIONAL"
        }}

    def grade_response(self, concept: str, is_correct: bool) -> float:
        current = self.mastery_scores.get(concept, 0.5)
        delta = 0.08 if is_correct else -0.05
        new_score = max(0.05, min(0.99, current + delta))
        self.mastery_scores[concept] = new_score
        return round(new_score, 3)
''',
            "src/main.py": f'''#!/usr/bin/env python3
"""
Education Tutor Server for {title}.
"""
import logging
from src.adaptive_engine import AdaptiveLearningEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("{clean_slug}")

def main():
    logger.info("Initializing {title} Learning Service...")
    engine = AdaptiveLearningEngine()
    next_task = engine.get_next_challenge()
    logger.info(f"Target Concept: {{next_task['target_concept']}} (Mastery: {{next_task['current_mastery']}}%)")

if __name__ == "__main__":
    main()
''',
            "tests/test_tutor.py": f'''import unittest
from src.adaptive_engine import AdaptiveLearningEngine

class TestEducation(unittest.TestCase):
    def test_adaptation(self):
        engine = AdaptiveLearningEngine()
        initial = engine.mastery_scores["Algorithms"]
        updated = engine.grade_response("Algorithms", True)
        self.assertGreater(updated, initial)

if __name__ == "__main__":
    unittest.main()
''',
            "curriculum.json": json.dumps({
                "course": title,
                "competencies": ["Foundations", "Application", "Analysis", "Synthesis"],
                "grading_scale": "MASTERY_BASED"
            }, indent=2)
        }

    elif domain == "climate":
        files = {
            "README.md": f"""# 🌱 {title} - Carbon Accounting & Smart Renewable Grid Optimization
> **Track**: {track} | **Team**: {team}  
> *{summary}*

## Environmental Impact
{problem}

## Core Algorithms
- **GHG Protocol Scope 1-3 Engine**: Quantifies real-time CO2 equivalents based on marginal grid emission factors.
- **Solar Insolation Forecaster**: Clearsky mathematical models predicting PV generation curves.
- **Demand Response Shifter**: Dispatches peak load shaving commands during high-carbon intensity hours.
""",
            "src/carbon_calculator.py": f'''"""
Emissions Factor Accounting & Marginal Grid Carbon Tracking.
"""
from typing import Dict, Any

class CarbonCalculator:
    # Marginal grid emissions factors (kg CO2e per kWh)
    GRID_FACTORS = {{
        "RENEWABLE_DOMINANT": 0.045,
        "MIXED_GRID": 0.380,
        "FOSSIL_HEAVY": 0.720
    }}

    def calculate_footprint(self, energy_kwh: float, grid_mode: str = "MIXED_GRID") -> Dict[str, Any]:
        factor = self.GRID_FACTORS.get(grid_mode, 0.380)
        kg_co2e = energy_kwh * factor
        trees_needed = kg_co2e / 21.0 # 21kg CO2 sequestered per mature tree per year

        return {{
            "energy_kwh": energy_kwh,
            "kg_co2e_emissions": round(kg_co2e, 2),
            "equivalent_trees_offset_years": round(trees_needed, 2),
            "sustainability_tier": "A+" if kg_co2e < 1.0 else ("B" if kg_co2e < 5.0 else "C")
        }}
''',
            "src/main.py": f'''#!/usr/bin/env python3
import logging
from src.carbon_calculator import CarbonCalculator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("{clean_slug}")

def main():
    logger.info("Initializing {title} CleanTech Engine...")
    calc = CarbonCalculator()
    res = calc.calculate_footprint(45.0, "RENEWABLE_DOMINANT")
    logger.info(f"Calculated: {{res['kg_co2e_emissions']}} kg CO2e (Tier: {{res['sustainability_tier']}})")

if __name__ == "__main__":
    main()
''',
            "tests/test_carbon.py": f'''import unittest
from src.carbon_calculator import CarbonCalculator

class TestClimate(unittest.TestCase):
    def test_carbon_calc(self):
        calc = CarbonCalculator()
        res = calc.calculate_footprint(10.0, "RENEWABLE_DOMINANT")
        self.assertLess(res["kg_co2e_emissions"], 1.0)
        self.assertEqual(res["sustainability_tier"], "A+")

if __name__ == "__main__":
    unittest.main()
''',
            "requirements.txt": "requests>=2.31.0\npydantic>=2.6.0\n"
        }

    else: # hardware
        files = {
            "README.md": f"""# 🔌 {title} - Open Hardware & Microcontroller Telemetry
> **Track**: {track} | **Team**: {team}  
> *{summary}*

## Hardware Schematics & Specifications
{problem}

## Firmware Architecture
- **I2C Bus Controller**: Scans and communicates with multi-sensor telemetry boards at 400kHz Fast Mode.
- **Hardware Watchdog Timer**: 100ms non-blocking reboot circuit preventing system lockups.
- **MQTT Serial Gateway**: Encapsulates 12-bit ADC raw readings into compressed JSON payloads.
""",
            "firmware/main.cpp": f'''/**
 * Microcontroller Firmware Entry for {title}
 * Target: ESP32-S3 / RP2040 Dual Core
 */
#include <stdio.h>

#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22
#define RELAY_PIN 14
#define BAUD_RATE 115200

void setup() {{
    printf("[BOOT] Initializing {title} Hardware Firmware...\\n");
    printf("[I2C] Bus online at 400kHz Fast Mode (SDA:%d, SCL:%d)\\n", I2C_SDA_PIN, I2C_SCL_PIN);
    printf("[GPIO] Relay Output Pin %d configured\\n", RELAY_PIN);
}}

void loop() {{
    // Simulated sensor acquisition cycle
    float voltage = 3.31f;
    int raw_adc = 2840; // 12-bit ADC
    printf("[TELEMETRY] Bus: %.2fV | ADC: %d | Status: NOMINAL\\n", voltage, raw_adc);
}}
''',
            "drivers/i2c_sensor.h": '''#ifndef I2C_SENSOR_H
#define I2C_SENSOR_H

#include <stdint.h>

struct SensorTelemetry {
    float temperature_c;
    float relative_humidity;
    uint32_t sample_index;
    uint8_t error_flags;
};

#endif
''',
            "src/serial_bridge.py": f'''"""
Host Serial to MQTT Gateway Bridge for {title}.
"""
import time
from typing import Dict, Any

class SerialBridge:
    def read_packet(self) -> Dict[str, Any]:
        return {{
            "device": "{clean_slug}_rev2",
            "voltage_rail": 3.32,
            "active_relays": [1],
            "ambient_temp_c": 22.4,
            "bus_status": "LOCKED_SYNC",
            "timestamp": time.time()
        }}
''',
            "tests/test_hardware.py": f'''import unittest
from src.serial_bridge import SerialBridge

class TestHardware(unittest.TestCase):
    def test_bridge_packet(self):
        bridge = SerialBridge()
        pkt = bridge.read_packet()
        self.assertEqual(pkt["bus_status"], "LOCKED_SYNC")
        self.assertAlmostEqual(pkt["voltage_rail"], 3.32, places=1)

if __name__ == "__main__":
    unittest.main()
''',
            "platformio.ini": f"""[env:esp32s3]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
monitor_speed = 115200
"""
        }

    return {
        "project_id": pid,
        "title": title,
        "team_name": team,
        "track_name": track,
        "domain": domain,
        "default_file": "README.md",
        "file_names": list(files.keys()),
        "files": files
    }

def get_project_demo_state(project: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates domain-tailored interactive demo metrics, controls, and runtime state.
    """
    pid = project.get("id", "prj_01")
    title = project.get("title", f"Project {pid}")
    summary = project.get("summary", "Autonomous hackathon module.")
    track = project.get("track_name", "General")
    domain = detect_project_domain(project)

    domain_configs = {
        "security": {
            "simulation_type": "Zero-Knowledge Cryptographic Shield & Threat Sandbox",
            "status": "ARMED · ZERO THREATS",
            "latency": "0.42 ms",
            "throughput": "12,400 ops/s",
            "metrics": {
                "Cipher Suite": "AES-256-GCM",
                "Entropy Pool": "4096 bits",
                "Tamper Proofs": "100% Passed",
                "Attacks Blocked": "1,842 mitigated"
            },
            "interactive_actions": [
                {"action": "SCAN_VULNERABILITIES", "label": "🛡️ Run Threat Scan", "desc": "Audits memory buffer and SQL injection vectors"},
                {"action": "GENERATE_KEYS", "label": "🔑 Rotate Ephemeral Keys", "desc": "Re-seeds Argon2id master key with fresh entropy"},
                {"action": "SIMULATE_INJECTION", "label": "⚠️ Simulate Cyber Attack", "desc": "Tests defense perimeter against SQLi and XSS payloads"}
            ],
            "initial_logs": [
                f"[SECURITY] Zero-knowledge proof subsystem booted for {title}",
                "[ENTROPY] Hardware RNG seeded 4096-bit master vault key",
                "[WAF] Heuristic threat filter active (0 malicious requests)",
                "[CIPHER] Constant-time signature verifier: ACTIVE",
                "[READY] Cryptographic sandbox ready for evaluator tests."
            ],
            "sandbox_type": "security",
            "sandbox_placeholder": "Enter secret text or SQL query (e.g. 'admin OR 1=1')..."
        },
        "devtools": {
            "simulation_type": "Sub-Millisecond Compiler & AST JIT Benchmark Sandbox",
            "status": "READY · OPTIMIZED",
            "latency": "0.18 ms",
            "throughput": "48,200 ops/s",
            "metrics": {
                "AST Parse Latency": "0.18 ms",
                "Constant Folding": "14 rules applied",
                "JIT Throughput": "142,500 ops/s",
                "Memory Overhead": "4.2 MB RSS"
            },
            "interactive_actions": [
                {"action": "RUN_BENCHMARK", "label": "⚡ Run 50k Benchmarks", "desc": "Tests execution speed of compiled bytecode"},
                {"action": "ANALYZE_AST", "label": "🌲 Parse AST Syntax Tree", "desc": "Constructs abstract syntax tree and optimizes dead nodes"},
                {"action": "OPTIMIZE_BYTECODE", "label": "🚀 Compile Bytecode", "desc": "Folds constants and eliminates unreachable branches"}
            ],
            "initial_logs": [
                f"[DEVTOOLS] Loaded {title} CLI runtime v2.4.0",
                "[AST] Syntax tree grammar verified without recursion limits",
                "[BENCHMARK] Micro-timer calibrated at 0.05 microsecond precision",
                "[READY] DevTools execution playground listening."
            ],
            "sandbox_type": "devtools",
            "sandbox_placeholder": "def compute(a, b): return (a * 2) + (10 + 20)"
        },
        "analytics": {
            "simulation_type": "Real-Time Telemetry Stream & Vector Embedding Sandbox",
            "status": "STREAMING · OPTIMAL",
            "latency": "1.12 ms",
            "throughput": "32,800 evt/s",
            "metrics": {
                "Stream Velocity": "32.8k evt/s",
                "Z-Score Filter": "Active (3.0 sigma)",
                "Vector Dimensions": "768-D Dense",
                "Model Accuracy": "99.4%"
            },
            "interactive_actions": [
                {"action": "INGEST_BATCH", "label": "📊 Ingest 10,000 Events", "desc": "Pushes live sensor telemetry into sliding window"},
                {"action": "RUN_ANOMALY_SCAN", "label": "🚨 Detect Anomaly Drift", "desc": "Computes Z-scores and Isolation Forest outliers"},
                {"action": "QUERY_VECTORS", "label": "🧬 Vector Similarity Search", "desc": "Performs cosine similarity query on embedded index"}
            ],
            "initial_logs": [
                f"[ANALYTICS] Ingestion pipeline calibrated for {title}",
                "[VECTOR] Initialized 768-dimensional cosine vector space",
                "[STREAM] Sliding window buffer configured (1,000 slots)",
                "[READY] Stream analytics engine awaiting incoming traffic."
            ],
            "sandbox_type": "analytics",
            "sandbox_placeholder": "Telemetry point value (e.g. 104.5 or 320.0 anomaly)..."
        },
        "accessibility": {
            "simulation_type": "WCAG 2.2 AAA Contrast & Multi-Modal Assistive Sandbox",
            "status": "VERIFIED · WCAG AAA",
            "latency": "0.35 ms",
            "throughput": "Live Audio/Tactile",
            "metrics": {
                "WCAG Rating": "AAA (Highest)",
                "Contrast Ratio": "14.2 : 1",
                "Speech Synthesis": "32 ms Latency",
                "Screen Reader Score": "100 / 100"
            },
            "interactive_actions": [
                {"action": "WCAG_AUDIT", "label": "👁️ Run WCAG Contrast Audit", "desc": "Calculates sRGB relative luminance and APCA ratings"},
                {"action": "SYNTHESIZE_SPEECH", "label": "🔊 Read Aloud via Voice", "desc": "Generates natural speech cadence for screen readers"},
                {"action": "SIMULATE_COLORBLIND", "label": "🎨 Test Deuteranopia Filter", "desc": "Applies chromatic adaptation for visual impairments"}
            ],
            "initial_logs": [
                f"[A11Y] Assistive bridge initialized for {title}",
                "[WCAG] Default color contrast evaluated: 14.2:1 (Passes AAA)",
                "[SPEECH] Phoneme synthesis engine online with 0 latency delay",
                "[READY] Assistive verification sandbox active."
            ],
            "sandbox_type": "accessibility",
            "sandbox_placeholder": "Text to evaluate for contrast and screen reader..."
        },
        "health": {
            "simulation_type": "Biometric Pulse & Cardiac Telemetry Monitor Sandbox",
            "status": "VITALS STABLE · HIPAA SAFE",
            "latency": "0.85 ms",
            "throughput": "250 Hz PPG/ECG",
            "metrics": {
                "Heart Rate": "72 BPM",
                "SpO2 Oxygenation": "98.8%",
                "ECG Rhythm": "Normal Sinus",
                "HIPAA Status": "De-Identified"
            },
            "interactive_actions": [
                {"action": "SAMPLE_VITALS", "label": "❤️ Read Live ECG / PPG", "desc": "Fetches current heart rate and pulse oximetry"},
                {"action": "TRIGGER_ARRHYTHMIA", "label": "🚨 Simulate Arrhythmia Event", "desc": "Simulates acute tachycardia for clinician alert testing"},
                {"action": "EXPORT_FHIR", "label": "📋 Generate HL7 FHIR Bundle", "desc": "Creates cryptographically anonymized health record"}
            ],
            "initial_logs": [
                f"[HEALTH] Telemetry monitor connected for {title}",
                "[ECG] PPG optical sensor stream calibrated at 250 Hz",
                "[HIPAA] Safe Harbor anonymization active (Zero PHI leakage)",
                "[READY] Real-time biometric vitals sandbox listening."
            ],
            "sandbox_type": "health",
            "sandbox_placeholder": "Patient note or observation..."
        },
        "education": {
            "simulation_type": "Adaptive Mastery & Knowledge Frontier Playground",
            "status": "ENGAGED · MASTERY 88%",
            "latency": "0.55 ms",
            "throughput": "Instant Grading",
            "metrics": {
                "Concept Mastery": "88.4%",
                "Retention Curve": "92.1% at 7d",
                "Bloom Taxonomy": "Level 4 (Analysis)",
                "Adaptive Index": "0.82 Optimal"
            },
            "interactive_actions": [
                {"action": "NEXT_CHALLENGE", "label": "📝 Next Adaptive Problem", "desc": "Generates challenge at the learner's mastery frontier"},
                {"action": "SUBMIT_CORRECT", "label": "✅ Submit Correct Answer", "desc": "Increases mastery score and advances learning graph"},
                {"action": "SUBMIT_INCORRECT", "label": "❌ Submit Flawed Answer", "desc": "Triggers remedial explanations and spaced repetition"}
            ],
            "initial_logs": [
                f"[EDUCATION] Adaptive graph initialized for {title}",
                "[CURRICULUM] 4 competency frontiers mapped (Level 4 Bloom)",
                "[IRT] Item Response Theory difficulty calibrated",
                "[READY] Adaptive learning playground active."
            ],
            "sandbox_type": "education",
            "sandbox_placeholder": "Student response or solution hypothesis..."
        },
        "climate": {
            "simulation_type": "Marginal Carbon Accounting & Clean Energy Grid Sandbox",
            "status": "RENEWABLE · TIER A+",
            "latency": "0.62 ms",
            "throughput": "Real-time kWh",
            "metrics": {
                "Carbon Offset": "412.5 kg CO2e",
                "Solar Generation": "14.8 kWh",
                "Renewable Mix": "88.2%",
                "Emissions Intensity": "0.045 kg/kWh"
            },
            "interactive_actions": [
                {"action": "CALCULATE_CARBON", "label": "🌱 Compute Carbon Offset", "desc": "Calculates net greenhouse gas emissions avoided"},
                {"action": "FORECAST_SOLAR", "label": "☀️ Forecast Solar Generation", "desc": "Simulates PV insolation under current irradiance"},
                {"action": "TRIGGER_LOAD_SHED", "label": "⚡ Shift Peak Grid Demand", "desc": "Balances grid frequency during peak carbon intensity"}
            ],
            "initial_logs": [
                f"[CLIMATE] Grid telemetry connected for {title}",
                "[GHG] Marginal emissions factor configured: 0.045 kg/kWh",
                "[SOLAR] PV insolation model loaded with 98% clear-sky yield",
                "[READY] Clean energy optimization sandbox active."
            ],
            "sandbox_type": "climate",
            "sandbox_placeholder": "Energy consumption in kWh (e.g. 50)..."
        },
        "hardware": {
            "simulation_type": "Virtual GPIO Breadboard & Microcontroller Bus Sandbox",
            "status": "ONLINE · I2C SYNC",
            "latency": "0.22 ms",
            "throughput": "400 kHz Fast Mode",
            "metrics": {
                "Bus Voltage": "3.31 V Rail",
                "UART Baud Rate": "115,200 bps",
                "12-bit ADC": "2840 counts",
                "Watchdog Timer": "100 ms Armed"
            },
            "interactive_actions": [
                {"action": "SCAN_I2C", "label": "🔌 Scan I2C Sensor Bus", "desc": "Polls 7-bit addresses on SDA/SCL pins"},
                {"action": "TOGGLE_RELAY", "label": "💡 Toggle GPIO Relay State", "desc": "Inverts digital pin 14 state (HIGH / LOW)"},
                {"action": "SAMPLE_ADC", "label": "📡 Sample 12-bit Analog ADC", "desc": "Reads raw analog sensor voltage on pin A0"}
            ],
            "initial_logs": [
                f"[HARDWARE] Microcontroller connected for {title}",
                "[I2C] Bus online at 400kHz Fast Mode (SDA:21, SCL:22)",
                "[WATCHDOG] 100ms hardware timer configured",
                "[READY] Virtual hardware bus sandbox listening."
            ],
            "sandbox_type": "hardware",
            "sandbox_placeholder": "Hex command (e.g. 0x3F 0x01)..."
        }
    }

    cfg = domain_configs.get(domain, domain_configs["devtools"])

    return {
        "project_id": pid,
        "title": title,
        "track": track,
        "domain": domain,
        "summary": summary,
        "simulation_type": cfg["simulation_type"],
        "status": cfg["status"],
        "latency": cfg["latency"],
        "throughput": cfg["throughput"],
        "metrics": cfg["metrics"],
        "interactive_actions": cfg["interactive_actions"],
        "initial_logs": cfg["initial_logs"],
        "sandbox_type": cfg["sandbox_type"],
        "sandbox_placeholder": cfg["sandbox_placeholder"]
    }
