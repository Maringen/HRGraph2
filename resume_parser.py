import re
import os
import sys
from typing import List, Dict, Any, Optional, Tuple, Callable
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTTextLineHorizontal, LTChar

class TextItem:
    def __init__(self, text: str, x: float, y: float, width: float, height: float, font_name: str, has_eol: bool = False):
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font_name = font_name
        self.has_eol = has_eol

    def __repr__(self):
        return f"TextItem(text='{self.text}', x={self.x:.2f}, y={self.y:.2f}, font='{self.font_name}')"

class OpenResumeParser:
    def __init__(self):
        self.section_title_keywords = [
            "experience", "education", "project", "skill",
            "job", "course", "extracurricular", "objective",
            "summary", "award", "honor", "expériences", "formation", "compétences", "projets", "langues"
        ]

    def parse(self, pdf_path: str) -> Dict[str, Any]:
        text_items = self.read_pdf(pdf_path)
        lines = self.group_text_items_into_lines(text_items)
        sections = self.group_lines_into_sections(lines)
        return self.extract_resume_from_sections(sections)

    def read_pdf(self, pdf_path: str) -> List[TextItem]:
        text_items = []
        for page_layout in extract_pages(pdf_path):
            elements = sorted(page_layout, key=lambda e: (-e.bbox[3], e.bbox[0]))
            for element in elements:
                if isinstance(element, LTTextContainer):
                    for text_line in element:
                        if isinstance(text_line, LTTextLineHorizontal):
                            line_text_items = []
                            for char in text_line:
                                if isinstance(char, LTChar):
                                    line_text_items.append(TextItem(
                                        text=char.get_text(),
                                        x=char.bbox[0],
                                        y=char.bbox[1],
                                        width=char.bbox[2] - char.bbox[0],
                                        height=char.bbox[3] - char.bbox[1],
                                        font_name=char.fontname
                                    ))
                            
                            if line_text_items:
                                merged = self.merge_chars(line_text_items)
                                if merged:
                                    merged[-1].has_eol = True
                                    text_items.extend(merged)
        return text_items

    def merge_chars(self, chars: List[TextItem]) -> List[TextItem]:
        if not chars: return []
        merged = []
        current = chars[0]
        typical_char_width = 5.0 # default
        
        for i in range(1, len(chars)):
            next_char = chars[i]
            # Merge if they are touching or very close
            if abs(next_char.x - (current.x + current.width)) < 2.0:
                current.text += next_char.text
                current.width = (next_char.x + next_char.width) - current.x
            else:
                merged.append(current)
                current = next_char
        merged.append(current)
        return merged

    def group_text_items_into_lines(self, text_items: List[TextItem]) -> List[List[TextItem]]:
        lines = []
        current_line = []
        for item in text_items:
            current_line.append(item)
            if item.has_eol:
                lines.append(current_line)
                current_line = []
        if current_line:
            lines.append(current_line)
        return lines

    def is_bold(self, item: TextItem) -> bool:
        return any(b in item.font_name.lower() for b in ["bold", "black", "heavy"])

    def has_letter_and_is_all_upper_case(self, item: TextItem) -> bool:
        return any(c.isalpha() for c in item.text) and item.text.upper() == item.text

    def has_only_letters_spaces_ampersands(self, item: TextItem) -> bool:
        return bool(re.match(r"^[a-zA-Z\s&À-ÿ]+$", item.text))

    def is_section_title(self, line: List[TextItem], line_number: int) -> bool:
        if line_number < 1 or len(line) > 2: # Section titles are usually short lines
            return False
        
        text = " ".join([i.text for i in line]).strip()
        if not text: return False
        
        item = line[0]
        # Heuristic 1: Bold and Uppercase
        if self.is_bold(item) and self.has_letter_and_is_all_upper_case(item):
            return True
            
        # Heuristic 2: Keywords and formatting
        words = [w for w in text.split(" ") if w != "&"]
        if len(words) <= 3 and text[0].isupper():
            low_text = text.lower()
            if any(kw in low_text for kw in self.section_title_keywords):
                # If it's bold OR contains only letters/spaces, it's likely a title
                if self.is_bold(item) or self.has_only_letters_spaces_ampersands(item):
                    return True
        return False

    def group_lines_into_sections(self, lines: List[List[TextItem]]) -> Dict[str, List[List[TextItem]]]:
        sections = {}
        section_name = "profile"
        section_lines = []
        
        for i, line in enumerate(lines):
            if self.is_section_title(line, i):
                sections[section_name.lower()] = section_lines
                section_name = " ".join([it.text for it in line]).strip()
                section_lines = []
            else:
                section_lines.append(line)
        
        sections[section_name.lower()] = section_lines
        return sections

    def extract_resume_from_sections(self, sections: Dict[str, List[List[TextItem]]]) -> Dict[str, Any]:
        profile = self.extract_profile(sections.get("profile", []))
        
        return {
            "profile": profile,
            "education": self.get_section_lines_by_keywords(sections, ["education", "formation"]),
            "experience": self.get_section_lines_by_keywords(sections, ["experience", "expériences", "emploi"]),
            "skills": self.extract_skills(sections),
        }

    def get_section_lines_by_keywords(self, sections: Dict[str, List[List[TextItem]]], keywords: List[str]) -> List[str]:
        for name, lines in sections.items():
            if any(kw in name.lower() for kw in keywords):
                return [" ".join([i.text for i in line]).strip() for line in lines]
        return []

    def extract_profile(self, lines: List[List[TextItem]]) -> Dict[str, Any]:
        items = [item for line in lines for item in line]
        
        # Name features
        name_feat = [
            (lambda i: re.match(r"^[a-zA-Z\s\.À-ÿ]+$", i.text), 3, True),
            (self.is_bold, 2, False),
            (self.has_letter_and_is_all_upper_case, 2, False),
            (lambda i: "@" in i.text, -10, False),
            (lambda i: re.search(r"\d", i.text), -10, False),
        ]
        
        # Email features
        email_feat = [
            (lambda i: re.search(r"[\w\.-]+@[\w\.-]+\.\w+", i.text), 10, True),
        ]
        
        # Phone features
        phone_feat = [
            (lambda i: re.search(r"(\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{2,4}[\s-]?\d{2,4}[\s-]?\d{2,4}", i.text), 10, True),
        ]

        name, _ = self.get_text_with_highest_feature_score(items, name_feat)
        email, _ = self.get_text_with_highest_feature_score(items, email_feat)
        phone, _ = self.get_text_with_highest_feature_score(items, phone_feat)
        
        return {
            "name": name,
            "email": email,
            "phone": phone
        }

    def get_text_with_highest_feature_score(self, items: List[TextItem], feature_sets: List[Tuple[Callable, int, bool]]) -> Tuple[str, List[float]]:
        text_items_with_scores = []
        seen_texts = set()
        
        for item in items:
            t = item.text.strip()
            if not t or t in seen_texts: continue
            seen_texts.add(t)

            total_score = 0
            possible = True
            for feat_func, score, is_required in feature_sets:
                res = feat_func(item)
                if res:
                    total_score += score
                elif is_required:
                    possible = False
                    break
            
            if possible:
                text_items_with_scores.append((t, total_score))
        
        if not text_items_with_scores: return "", []
        text_items_with_scores.sort(key=lambda x: x[1], reverse=True)
        return text_items_with_scores[0][0], [s for t, s in text_items_with_scores]

    def extract_skills(self, sections: Dict[str, List[List[TextItem]]]) -> List[str]:
        lines = self.get_section_lines_by_keywords(sections, ["skill", "compétences"])
        skills = []
        for line in lines:
            parts = re.split(r"[,;•|·\t]", line)
            skills.extend([p.strip() for p in parts if len(p.strip()) > 1])
        return list(set(skills))

if __name__ == "__main__":
    parser = OpenResumeParser()
    path = sys.argv[1] if len(sys.argv) > 1 else "hr_vault/CV1.pdf"
    res = parser.parse(path)
    import json
    print(json.dumps(res, indent=2, ensure_ascii=False))
