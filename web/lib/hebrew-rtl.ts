/**
 * Detect and handle Hebrew/RTL text for Satori OG image rendering.
 * Satori doesn't support RTL text properly, so we reverse the character order
 * for Hebrew text to work around this limitation.
 */

const HEBREW_RANGE = /[\u0590-\u05FF]/g;

export function hasHebrew(text: string): boolean {
  return HEBREW_RANGE.test(text);
}

export function reverseHebrewText(text: string): string {
  if (!hasHebrew(text)) {
    return text;
  }

  // Split into array of characters (handling emojis and multi-byte chars)
  const chars = Array.from(text);
  
  // Reverse the order
  return chars.reverse().join('');
}

export function processTextForSatori(text: string): string {
  return reverseHebrewText(text);
}
