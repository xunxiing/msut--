function shouldForceBlob(downloadName?: string) {
  if (!downloadName) return false
  const lower = downloadName.toLowerCase()
  return lower.endsWith('.melsave') || lower.endsWith('.melmod')
}

async function downloadViaBlob(href: string, downloadName: string) {
  const resp = await fetch(href, { credentials: 'include' })
  if (!resp.ok) throw new Error(`download failed: ${resp.status}`)
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  try {
    const link = document.createElement('a')
    link.href = url
    link.download = downloadName || ''
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } finally {
    URL.revokeObjectURL(url)
  }
}

export function triggerFileDownload(href: string, downloadName?: string) {
  if (!href) return

  if (downloadName && shouldForceBlob(downloadName)) {
    downloadViaBlob(href, downloadName).catch(() => {
      const link = document.createElement('a')
      link.href = href
      link.download = downloadName || ''
      link.style.display = 'none'
      document.body.appendChild(link)
      try {
        link.click()
      } finally {
        document.body.removeChild(link)
      }
    })
    return
  }

  const link = document.createElement('a')
  link.href = href
  if (downloadName !== undefined) {
    // Explicitly set download even for empty string so the browser honors Content-Disposition.
    link.download = downloadName || ''
  }
  link.style.display = 'none'
  document.body.appendChild(link)
  try {
    link.click()
  } finally {
    document.body.removeChild(link)
  }
}
