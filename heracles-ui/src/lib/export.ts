type ExportRow = Record<string, unknown>

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function serializeValue(value: unknown) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

function escapeCsv(value: string) {
  if (value.includes('"') || value.includes(',') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

export function exportToCsv({
  data,
  columns,
  filename,
}: {
  data: ExportRow[]
  columns?: string[]
  filename: string
}) {
  if (!data.length) {
    downloadBlob(new Blob([''], { type: 'text/csv;charset=utf-8;' }), filename)
    return
  }

  const headers = columns && columns.length > 0 ? columns : Object.keys(data[0])
  const lines = [
    headers.join(','),
    ...data.map((row) =>
      headers
        .map((header) => escapeCsv(serializeValue(row[header])))
        .join(',')
    ),
  ]

  downloadBlob(
    new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' }),
    filename
  )
}

export function exportToJson({
  data,
  filename,
}: {
  data: ExportRow[]
  filename: string
}) {
  const json = JSON.stringify(data, null, 2)
  downloadBlob(new Blob([json], { type: 'application/json' }), filename)
}
