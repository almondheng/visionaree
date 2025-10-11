import type { ClassValue } from 'clsx'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format seconds into HH:MM:SS or MM:SS format
 */
export function formatTimestamp(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes
      .toString()
      .padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return `${minutes.toString().padStart(2, '0')}:${secs
    .toString()
    .padStart(2, '0')}`
}

/**
 * Parse timestamp string (HH:MM:SS or MM:SS) into seconds
 */
export function parseTimestamp(timestamp: string): number {
  const parts = timestamp
    .split(':')
    .map(Number)
    .filter(n => !isNaN(n))

  if (parts.length === 3) {
    // HH:MM:SS
    return (parts[0] || 0) * 3600 + (parts[1] || 0) * 60 + (parts[2] || 0)
  } else if (parts.length === 2) {
    // MM:SS
    return (parts[0] || 0) * 60 + (parts[1] || 0)
  }

  return 0
}

/**
 * Format absolute timestamp from caption timestamp
 */
export function formatAbsoluteTimestamp(timestamp: number): string {
  const date = new Date(timestamp) // timestamp is already in milliseconds from Date.now()
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}
