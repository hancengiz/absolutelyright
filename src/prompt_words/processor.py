"""Word processing and counting logic for prompt words."""
import re
from typing import Dict, List, Set, Tuple


class WordProcessor:
    """Processes user messages and counts words based on patterns."""

    def __init__(
        self,
        tracked_words: Dict[str, str],
        filtered_words: Dict[str, str] = None,
        filter_mode: str = "track_separately"
    ):
        """
        Initialize word processor.

        Args:
            tracked_words: Dictionary of word_name -> regex_pattern
            filtered_words: Dictionary of filter_name -> regex_pattern for filtered words
            filter_mode: How to handle filtered words:
                - "track_separately": Track as combined "filtered" count
                - "exclude": Don't track filtered words
                - "show_all": Track everything (no filtering)
        """
        self.tracked_words = tracked_words
        self.filtered_words = filtered_words or {}
        self.filter_mode = filter_mode

        # Compile regex patterns for performance
        self.compiled_tracked = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in tracked_words.items()
        }
        self.compiled_filtered = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.filtered_words.items()
        }

    def process_text(self, text: str) -> Dict[str, int]:
        """
        Process text and return word counts.

        Args:
            text: Text to process

        Returns:
            Dictionary of word_name -> count (1 if found, 0 if not)
            Note: Each word is counted once per message (boolean presence)
        """
        counts = {}
        found_filtered = False

        # Check tracked words
        for word_name, pattern in self.compiled_tracked.items():
            if pattern.search(text):
                counts[word_name] = 1
            else:
                counts[word_name] = 0

        # Check filtered words
        if self.filter_mode != "show_all":
            for filter_name, pattern in self.compiled_filtered.items():
                if pattern.search(text):
                    found_filtered = True
                    break

        # Handle filtered words based on mode
        if found_filtered:
            if self.filter_mode == "track_separately":
                counts["filtered"] = 1
            elif self.filter_mode == "exclude":
                # Remove all tracked words if message contains filtered words
                counts = {word: 0 for word in counts}

        # Add filtered count if not found and we're tracking separately
        if self.filter_mode == "track_separately" and "filtered" not in counts:
            counts["filtered"] = 0

        return counts

    def process_messages(self, messages: List[str]) -> Dict[str, int]:
        """
        Process multiple messages and aggregate counts.

        Args:
            messages: List of message texts

        Returns:
            Dictionary of word_name -> total_count across all messages
        """
        aggregated = {}

        for message in messages:
            counts = self.process_text(message)
            for word, count in counts.items():
                aggregated[word] = aggregated.get(word, 0) + count

        return aggregated

    def is_filtered(self, text: str) -> bool:
        """Check if text contains any filtered words."""
        for pattern in self.compiled_filtered.values():
            if pattern.search(text):
                return True
        return False

    def get_matched_words(self, text: str) -> Set[str]:
        """Return set of word names that matched in the text."""
        matched = set()

        for word_name, pattern in self.compiled_tracked.items():
            if pattern.search(text):
                matched.add(word_name)

        if self.filter_mode == "track_separately" and self.is_filtered(text):
            matched.add("filtered")

        return matched
