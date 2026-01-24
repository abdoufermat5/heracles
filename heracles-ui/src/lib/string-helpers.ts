/**
 * String Helper Utilities
 *
 * Common string manipulation functions used across the application.
 */

/**
 * Converts an array of strings to a comma-separated string.
 *
 * @param arr - Array of strings to convert
 * @param separator - Separator to use between items (default: ', ')
 * @returns Comma-separated string or empty string if array is undefined/empty
 *
 * @example
 * arrayToString(['a', 'b', 'c']) // 'a, b, c'
 * arrayToString(undefined) // ''
 */
export function arrayToString(
  arr: string[] | undefined,
  separator = ', '
): string {
  return arr?.join(separator) ?? ''
}

/**
 * Converts a comma-separated string to an array of trimmed strings.
 * Filters out empty strings.
 *
 * @param str - String to split
 * @param separator - Separator to split on (default: ',')
 * @returns Array of trimmed, non-empty strings
 *
 * @example
 * stringToArray('a, b, c') // ['a', 'b', 'c']
 * stringToArray('  a , b ,  ') // ['a', 'b']
 * stringToArray(undefined) // []
 */
export function stringToArray(
  str: string | undefined,
  separator = ','
): string[] {
  if (!str) return []
  return str
    .split(separator)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

/**
 * Alias for stringToArray for backward compatibility.
 * @deprecated Use stringToArray instead
 */
export const parseStringToArray = stringToArray
