/**
 * Detect and handle Hebrew/RTL text for Satori OG image rendering.
 * Satori doesn't fully support RTL, so we reverse only the Hebrew character
 * segments while keeping English/Latin segments intact.
 */

const HEBREW_CHAR = /[\u0590-\u05FF]/;

export function hasHebrew(text: string): boolean {
  return HEBREW_CHAR.test(text);
}

export function reverseHebrewText(text: string): string {
  if (!hasHebrew(text)) {
    return text;
  }

  // Split into segments of Hebrew vs non-Hebrew, reverse only Hebrew segments
  const chars = Array.from(text);
  let result = "";
  let segment = "";
  let segmentIsHebrew = false;

  for (const ch of chars) {
    const chIsHebrew = HEBREW_CHAR.test(ch);

    if (segment === "") {
      segment = ch;
      segmentIsHebrew = chIsHebrew;
    } else if (chIsHebrew === segmentIsHebrew) {
      segment += ch;
    } else {
      // Flush previous segment
      result += segmentIsHebrew
        ? Array.from(segment).reverse().join("")
        : segment;
      segment = ch;
      segmentIsHebrew = chIsHebrew;
    }
  }

  // Flush final segment
  if (segment) {
    result += segmentIsHebrew
      ? Array.from(segment).reverse().join("")
      : segment;
  }

  return result;
}

export function processTextForSatori(text: string): string {
  return reverseHebrewText(text);
}
