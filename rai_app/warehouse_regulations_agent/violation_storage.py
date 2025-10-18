"""
Violation storage module for SafetyAgent.

This module provides a dedicated class for managing safety violation storage,
including persistence, querying, and data management.
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List


class ViolationStorage:
    """Handles storage, persistence, and querying of safety violations."""

    def __init__(self, violations_file: str = "safety_violations.json"):
        """
        Initialize violation storage.

        Args:
            violations_file: Path to the JSON file for storing violations
        """
        self.violations_file = violations_file

        # Violation storage
        self.violations_history: List[Dict[str, Any]] = []
        self.violations_by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.violations_count: Dict[str, int] = defaultdict(int)

        # Load existing violations
        self._load_violations()

    def _load_violations(self) -> None:
        """Load violations from file if it exists."""
        try:
            with open(self.violations_file, "r") as f:
                data = json.load(f)
                self.violations_history = data.get("violations_history", [])
                self.violations_by_type = defaultdict(
                    list, data.get("violations_by_type", {})
                )
                self.violations_count = defaultdict(
                    int, data.get("violations_count", {})
                )
            print(
                f"Loaded {len(self.violations_history)} violations from {self.violations_file}"
            )
        except FileNotFoundError:
            print(f"No existing violations file found at {self.violations_file}")
        except Exception as e:
            print(f"Error loading violations: {e}")

    def _save_violations(self) -> None:
        """Save violations to file."""
        try:
            data = {
                "violations_history": self.violations_history,
                "violations_by_type": dict(self.violations_by_type),
                "violations_count": dict(self.violations_count),
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.violations_file, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(
                f"Saved {len(self.violations_history)} violations to {self.violations_file}"
            )
        except Exception as e:
            print(f"Error saving violations: {e}")

    def store_violations(self, violations: List[Dict[str, Any]]) -> None:
        """
        Store violations in memory and persist to file.

        Args:
            violations: List of violation dictionaries to store
        """
        timestamp = datetime.now().isoformat()

        for violation in violations:
            # Add timestamp and unique ID
            violation_record = {
                "id": f"{timestamp}_{len(self.violations_history)}",
                "timestamp": timestamp,
                "violation": violation,
            }

            # Store in history
            self.violations_history.append(violation_record)

            # Store by type
            violation_type = violation.get("type", "unknown")
            self.violations_by_type[violation_type].append(violation_record)

            # Update count
            self.violations_count[violation_type] += 1

        # Persist to file
        self._save_violations()

    def get_violations_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all stored violations.

        Returns:
            Dictionary containing violation summary statistics
        """
        return {
            "total_violations": len(self.violations_history),
            "violations_by_type": dict(self.violations_count),
            "recent_violations": self.violations_history[-10:]
            if self.violations_history
            else [],
            "last_updated": datetime.now().isoformat(),
        }

    def get_violations_by_type(self, violation_type: str) -> List[Dict[str, Any]]:
        """
        Get all violations of a specific type.

        Args:
            violation_type: Type of violations to retrieve

        Returns:
            List of violation records of the specified type
        """
        return self.violations_by_type.get(violation_type, [])

    def get_recent_violations(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Get the n most recent violations.

        Args:
            n: Number of recent violations to retrieve

        Returns:
            List of the n most recent violation records
        """
        return self.violations_history[-n:] if self.violations_history else []

    def get_violations_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """
        Get all violations of a specific severity level.

        Args:
            severity: Severity level to filter by (e.g., 'high', 'medium', 'low')

        Returns:
            List of violation records with the specified severity
        """
        return [
            record
            for record in self.violations_history
            if record["violation"].get("severity", "").lower() == severity.lower()
        ]

    def get_violations_by_location(self, location: str) -> List[Dict[str, Any]]:
        """
        Get all violations at a specific location.

        Args:
            location: Location to filter by

        Returns:
            List of violation records at the specified location
        """
        return [
            record
            for record in self.violations_history
            if record["violation"].get("location", "").lower() == location.lower()
        ]

    def get_violations_in_timeframe(
        self, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """
        Get violations within a specific timeframe.

        Args:
            start_time: Start time in ISO format
            end_time: End time in ISO format

        Returns:
            List of violation records within the specified timeframe
        """
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        return [
            record
            for record in self.violations_history
            if start_dt <= datetime.fromisoformat(record["timestamp"]) <= end_dt
        ]

    def get_violation_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics about stored violations.

        Returns:
            Dictionary containing detailed violation statistics
        """
        if not self.violations_history:
            return {
                "total_violations": 0,
                "violations_by_type": {},
                "violations_by_severity": {},
                "violations_by_location": {},
                "time_span": None,
                "average_violations_per_day": 0,
            }

        # Calculate statistics
        violations_by_severity = defaultdict(int)
        violations_by_location = defaultdict(int)

        timestamps = []
        for record in self.violations_history:
            violation = record["violation"]
            violations_by_severity[violation.get("severity", "unknown")] += 1
            violations_by_location[violation.get("location", "unknown")] += 1
            timestamps.append(datetime.fromisoformat(record["timestamp"]))

        # Calculate time span
        if timestamps:
            time_span = (max(timestamps) - min(timestamps)).days
            avg_per_day = len(self.violations_history) / max(time_span, 1)
        else:
            time_span = 0
            avg_per_day = 0

        return {
            "total_violations": len(self.violations_history),
            "violations_by_type": dict(self.violations_count),
            "violations_by_severity": dict(violations_by_severity),
            "violations_by_location": dict(violations_by_location),
            "time_span_days": time_span,
            "average_violations_per_day": round(avg_per_day, 2),
            "first_violation": min(timestamps).isoformat() if timestamps else None,
            "last_violation": max(timestamps).isoformat() if timestamps else None,
        }

    def clear_violations(self) -> None:
        """Clear all stored violations."""
        self.violations_history.clear()
        self.violations_by_type.clear()
        self.violations_count.clear()
        self._save_violations()
        print("All violations cleared")

    def export_violations(self, export_file: str, format: str = "json") -> None:
        """
        Export violations to a file in the specified format.

        Args:
            export_file: Path to the export file
            format: Export format ('json' or 'csv')
        """
        if format.lower() == "json":
            with open(export_file, "w") as f:
                json.dump(
                    self.get_violations_summary(), f, indent=2, ensure_ascii=False
                )
        elif format.lower() == "csv":
            import csv

            with open(export_file, "w", newline="") as f:
                if self.violations_history:
                    fieldnames = [
                        "id",
                        "timestamp",
                        "type",
                        "description",
                        "severity",
                        "location",
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for record in self.violations_history:
                        violation = record["violation"]
                        writer.writerow(
                            {
                                "id": record["id"],
                                "timestamp": record["timestamp"],
                                "type": violation.get("type", ""),
                                "description": violation.get("description", ""),
                                "severity": violation.get("severity", ""),
                                "location": violation.get("location", ""),
                            }
                        )
        else:
            raise ValueError(f"Unsupported export format: {format}")

        print(f"Violations exported to {export_file} in {format.upper()} format")

    def search_violations(self, query: str) -> List[Dict[str, Any]]:
        """
        Search violations by description or type.

        Args:
            query: Search query string

        Returns:
            List of violation records matching the query
        """
        query_lower = query.lower()
        matches = []

        for record in self.violations_history:
            violation = record["violation"]
            if (
                query_lower in violation.get("description", "").lower()
                or query_lower in violation.get("type", "").lower()
            ):
                matches.append(record)

        return matches

    def get_violation_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Get violation trends over the specified number of days.

        Args:
            days: Number of days to analyze trends for

        Returns:
            Dictionary containing trend analysis
        """
        if not self.violations_history:
            return {"trend": "no_data", "daily_counts": []}

        # Calculate daily counts
        daily_counts = defaultdict(int)
        for record in self.violations_history:
            date = datetime.fromisoformat(record["timestamp"]).date()
            daily_counts[date] += 1

        # Sort by date
        sorted_dates = sorted(daily_counts.keys())
        daily_data = [
            {"date": str(date), "count": daily_counts[date]} for date in sorted_dates
        ]

        # Calculate trend
        if len(daily_data) >= 2:
            recent_avg = sum(d["count"] for d in daily_data[-7:]) / min(
                7, len(daily_data)
            )
            older_avg = sum(d["count"] for d in daily_data[:-7]) / max(
                1, len(daily_data) - 7
            )

            if recent_avg > older_avg * 1.1:
                trend = "increasing"
            elif recent_avg < older_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "daily_counts": daily_data,
            "total_days": len(daily_data),
            "average_per_day": round(
                sum(d["count"] for d in daily_data) / max(1, len(daily_data)), 2
            ),
        }
