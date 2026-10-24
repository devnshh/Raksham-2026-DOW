"""
SATARK Model Client Abstraction.
Provides a unified interface (ModelClient) with two implementations:
- HttpModelClient: For production/distributed deployment where model runs on port 8001.
  Uses shared httpx.Client with connection pooling, 300ms timeout, and 1 fast connection retry.
- LocalModelClient: For local development and unit tests where model runs in-process.
Selected automatically via MODEL_SERVICE_URL environment variable.
"""

import os
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger("satark.model_client")

# One copy of the trained bundle lives in model_service/models/ and both clients use it.
_MODELS_DIR = Path(__file__).resolve().parent.parent / "model_service" / "models"
MODEL_FILE = _MODELS_DIR / "satark_model.joblib"
THRESHOLDS_FILE = _MODELS_DIR / "thresholds.json"


class ModelServiceError(Exception):
    """Base exception for all model client and inference failures."""
    pass


class ModelValidationError(ModelServiceError):
    """Raised when model service rejects input due to missing features (HTTP 422)."""
    pass


class ModelConnectionError(ModelServiceError):
    """Raised when connecting to the model service fails after retry."""
    pass


class ModelTimeoutError(ModelServiceError):
    """Raised when model service call exceeds the 300 ms SLA."""
    pass


class ModelClient(ABC):
    """Abstract interface defining the scoring and threshold contract."""

    @abstractmethod
    def score(self, features: Dict[str, Any], note_intent: str = "none") -> Dict[str, Any]:
        """
        Executes model inference on the provided feature vector.
        Returns:
            dict containing:
                - fusion_score (float)
                - tier_hint (Optional[str])
                - reasons (List[str])
        Raises:
            ModelServiceError, ModelValidationError, ModelConnectionError, ModelTimeoutError
        """
        pass

    @property
    @abstractmethod
    def thr(self) -> Optional[Dict[str, float]]:
        """Returns threshold cutoffs dict with 'amber' and 'red' values."""
        pass


class LocalModelClient(ModelClient):
    """
    Executes model inference in-process using SatarkScorer directly.
    Selected when MODEL_SERVICE_URL is not configured.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        thresholds_path: Optional[str] = None
    ):
        from model_service.satark_scorer import SatarkScorer

        m_path = model_path or os.getenv("SATARK_MODEL_PATH", str(MODEL_FILE))
        t_path = thresholds_path or os.getenv("SATARK_THRESHOLDS_PATH", str(THRESHOLDS_FILE))

        self.scorer = SatarkScorer(m_path, t_path if Path(t_path).exists() else None)

    @property
    def thr(self) -> Optional[Dict[str, float]]:
        return self.scorer.thr

    def score(self, features: Dict[str, Any], note_intent: str = "none") -> Dict[str, Any]:
        try:
            return self.scorer.score(features, note_intent=note_intent)
        except ValueError as val_err:
            err_msg = str(val_err)
            if "Missing features" in err_msg:
                raise ModelValidationError(err_msg)
            raise ModelServiceError(err_msg)
        except Exception as exc:
            raise ModelServiceError(f"Local model scoring failed: {str(exc)}")


class HttpModelClient(ModelClient):
    """
    Connects to the standalone Model Service (port 8001) over HTTP.
    Maintains a shared connection-pooled httpx.Client with 300 ms timeout
    and exactly one fast retry on connection errors.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout_seconds: float = 0.300,
        client: Optional[httpx.Client] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("MODEL_SERVICE_KEY")
        if not self.api_key:
            raise ModelServiceError(
                "MODEL_SERVICE_KEY must be set (same value for the Risk API and the Model Service) "
                "when MODEL_SERVICE_URL is used"
            )
        self.timeout_seconds = timeout_seconds

        if client is not None:
            self._client = client
        else:
            # Shared HTTP client with connection pooling
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
            timeout = httpx.Timeout(timeout_seconds, connect=0.150)
            self._client = httpx.Client(limits=limits, timeout=timeout)

        self._cached_thr = self._load_thresholds()

    def _load_thresholds(self) -> Dict[str, float]:
        """Loads the same thresholds file the Model Service uses (single source of truth)."""
        thr_file = Path(os.getenv("SATARK_THRESHOLDS_PATH", str(THRESHOLDS_FILE)))
        data = json.loads(thr_file.read_text(encoding="utf-8"))
        return {"amber": float(data["amber"]), "red": float(data["red"])}

    @property
    def thr(self) -> Optional[Dict[str, float]]:
        return self._cached_thr

    def score(self, features: Dict[str, Any], note_intent: str = "none") -> Dict[str, Any]:
        url = f"{self.base_url}/score"
        headers = {
            "Content-Type": "application/json",
            "X-Internal-Key": self.api_key
        }
        payload = {
            "features": features,
            "note_intent": note_intent or "none"
        }

        # Attempt call with exactly one fast retry only on connection errors
        resp = None
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                resp = self._client.post(url, json=payload, headers=headers)
                break
            except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
                if attempt == 0:
                    # One fast retry on connection error
                    time.sleep(0.005)
                    continue
                logger.error(f"Model service connection failed after retry: {conn_err}")
                raise ModelConnectionError(f"Cannot connect to model service at {self.base_url}: {conn_err}")
            except httpx.TimeoutException as timeout_err:
                # Read/Write/Pool timeout: DO NOT retry
                logger.error(f"Model service timed out after {self.timeout_seconds}s: {timeout_err}")
                raise ModelTimeoutError(f"Model service timeout: {timeout_err}")
            except Exception as exc:
                logger.error(f"Unexpected error calling model service: {exc}")
                raise ModelServiceError(f"Client error calling model service: {exc}")

        if resp is None:
            raise ModelServiceError("No response received from model service")

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 422:
            raise ModelValidationError(f"Missing required features from model service: {resp.text}")
        elif resp.status_code in (401, 403):
            raise ModelServiceError(f"Unauthorized: model service rejected API key (HTTP {resp.status_code})")
        else:
            raise ModelServiceError(f"Model service returned HTTP {resp.status_code}: {resp.text}")

    def close(self):
        """Closes the underlying httpx client."""
        if hasattr(self, "_client") and self._client:
            self._client.close()


_singleton_client: Optional[ModelClient] = None


def get_model_client(reload: bool = False) -> ModelClient:
    """
    Returns the configured ModelClient instance.
    If MODEL_SERVICE_URL is set, returns HttpModelClient.
    Otherwise, returns in-process LocalModelClient.
    """
    global _singleton_client
    if _singleton_client is None or reload:
        service_url = os.getenv("MODEL_SERVICE_URL")
        if service_url and service_url.strip():
            _singleton_client = HttpModelClient(base_url=service_url.strip())
        else:
            _singleton_client = LocalModelClient()
    return _singleton_client
