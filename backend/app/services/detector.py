"""Repetition and Sequence Pattern Detector Service.

Analyzes an event stream to discover recurring sequences of user actions.
Identifies cross-application workflows (e.g. Gmail -> Download -> CRM -> Slack)
and calculates occurrence counts and confidence scores.
"""
import hashlib
from typing import List, Tuple, Dict, Optional
from ..models.event import UserEvent, DetectedSequence


def _format_step_title(app: str, action: str) -> str:
    """Format readable step titles from app and action."""
    clean_app = app.split(" (")[0]
    action_title = action.replace("_", " ").title()
    return f"{clean_app}: {action_title}"


def _calculate_confidence(occurrence_count: int, sequence_length: int) -> float:
    """Calculate confidence score based on repeated occurrences and sequence length.
    
    Formula:
    - Base confidence scales with occurrence count.
    - Additional confidence boost for multi-step workflows.
    - Capped at 0.98.
    """
    if occurrence_count < 2:
        return 0.40
    
    base = 0.60 + (occurrence_count * 0.10)
    if sequence_length >= 4:
        base += 0.05
    return round(min(0.98, max(0.50, base)), 2)


def _find_non_overlapping_occurrences(tokens: List[str], target_subseq: Tuple[str, ...]) -> List[int]:
    """Find all start indices of non-overlapping occurrences of target_subseq in tokens."""
    L = len(target_subseq)
    occurrences: List[int] = []
    i = 0
    while i <= len(tokens) - L:
        if tuple(tokens[i : i + L]) == target_subseq:
            occurrences.append(i)
            i += L
        else:
            i += 1
    return occurrences


class PatternDetectorService:
    def detect_patterns(
        self,
        events: List[UserEvent],
        min_occurrences: int = 2,
        window_size: Optional[int] = None,
        min_length: int = 2,
        max_length: int = 6,
    ) -> List[DetectedSequence]:
        """Scans the event stream for repetitive sequences of actions across apps.
        
        Args:
            events: List of observed UserEvent objects.
            min_occurrences: Minimum number of times a sequence must repeat (default: 2).
            window_size: Fixed sequence length to search for. If None, searches min_length..max_length.
            min_length: Minimum sequence length when auto-searching (default: 2).
            max_length: Maximum sequence length when auto-searching (default: 6).
            
        Returns:
            List of DetectedSequence objects sorted by occurrence count and sequence length.
        """
        if not events or len(events) < min_occurrences * min_length:
            return []

        # Create signature tokens for each event: e.g. "Gmail (Chrome):open_email"
        tokens = [f"{e.app}:{e.action}" for e in events]
        total_tokens = len(tokens)

        # Determine lengths to evaluate
        if window_size is not None:
            lengths_to_check = [window_size]
        else:
            # Check longer sequences first to prioritize maximal patterns
            effective_max = min(max_length, total_tokens // min_occurrences)
            lengths_to_check = list(range(effective_max, min_length - 1, -1))

        candidates: Dict[Tuple[str, ...], List[int]] = {}

        for length in lengths_to_check:
            for i in range(total_tokens - length + 1):
                subseq = tuple(tokens[i : i + length])
                if subseq not in candidates:
                    occurrences = _find_non_overlapping_occurrences(tokens, subseq)
                    if len(occurrences) >= min_occurrences:
                        candidates[subseq] = occurrences

        # Sort candidate subseqs by occurrence count descending, then length descending
        sorted_subseqs = sorted(candidates.keys(), key=lambda s: (len(candidates[s]), len(s)), reverse=True)

        filtered_subseqs: List[Tuple[str, ...]] = []

        for subseq in sorted_subseqs:
            count = len(candidates[subseq])
            is_redundant = False
            subseq_str = " | ".join(subseq)

            for accepted in filtered_subseqs:
                accepted_count = len(candidates[accepted])

                # Check if subseq is a sub-slice or cyclical rotation of an already accepted dominant sequence
                double_accepted = accepted + accepted
                double_str = " | ".join(double_accepted)

                if subseq_str in double_str and accepted_count >= count:
                    is_redundant = True
                    break

            if not is_redundant:
                filtered_subseqs.append(subseq)

        # Build DetectedSequence results
        results: List[DetectedSequence] = []
        for idx, subseq in enumerate(filtered_subseqs, start=1):
            occurrences = candidates[subseq]
            occurrence_count = len(occurrences)
            first_idx = occurrences[0]
            seq_len = len(subseq)
            sample_events = events[first_idx : first_idx + seq_len]

            # Deterministic, unique pattern ID
            sig_hash = hashlib.md5(" -> ".join(subseq).encode("utf-8")).hexdigest()[:8]
            pattern_id = f"pat_{sig_hash}"

            signature = " -> ".join(subseq)
            steps_summary = [_format_step_title(e.app, e.action) for e in sample_events]
            confidence = _calculate_confidence(occurrence_count, seq_len)

            unique_apps = len(set(e.app for e in sample_events))
            description = (
                f"Repeated workflow detected ({seq_len} steps across {unique_apps} apps), "
                f"occurring {occurrence_count} times with {int(confidence * 100)}% confidence."
            )

            results.append(
                DetectedSequence(
                    pattern_id=pattern_id,
                    signature=signature,
                    steps_summary=steps_summary,
                    occurrence_count=occurrence_count,
                    confidence_score=confidence,
                    sample_events=sample_events,
                    description=description,
                )
            )

        # Sort by occurrence_count descending, then confidence_score descending
        results.sort(key=lambda r: (r.occurrence_count, r.confidence_score, len(r.steps_summary)), reverse=True)
        return results


detector_service = PatternDetectorService()
