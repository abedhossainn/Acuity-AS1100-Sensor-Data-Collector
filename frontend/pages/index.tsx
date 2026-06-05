import React, { useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type ApiConnection = {
  port: string
  description?: string
}

type ActiveConnection = {
  port: string
  name: string
  active: boolean
  status: 'Ready' | 'Collecting' | 'Stopped'
}

type SensorSample = {
  timestamp?: string
  values?: Record<string, string>
}

type HistoryItem = {
  session_id: string
  file_count: number
  total_size_bytes: number
  last_updated: string
}

type SystemInfo = {
  os: string
  in_container: boolean
  sensor_provider?: string
  provider_note?: string
  agent_reachable?: boolean | null
  agent_reason?: string
  port_count: number
  ports: ApiConnection[]
  serial_note?: string
  timestamp_timezone_name?: string
  timestamp_utc_offset_minutes?: number
  timestamp_utc_offset_label?: string
}

type SerialProfile = '7E1' | '8N1'

type Capabilities = {
  supported_baud_rates: number[]
  supported_serial_profiles: SerialProfile[]
  baud_max_hz: Record<string, number>
  measuring_mode_max_hz: Record<string, number>
  frequency_presets_hz: number[]
}

type RateProbeResult = {
  target_hz: number
  achieved_hz: number
  samples: number
  duration_seconds: number
  stable: boolean
  note?: string
}

type RateProbeResponse = {
  port: string
  baud_rate: number
  measuring_mode: string
  duration_seconds: number
  static_max_hz: number
  recommended_max_hz: number
  results: RateProbeResult[]
}

type ConnectionDoctorAttempt = {
  baud_rate: number
  serial_profile: SerialProfile
  success: boolean
  detail?: string
}

type ConnectionDoctorResponse = {
  port: string
  sensor_id: number
  attempted: ConnectionDoctorAttempt[]
  recommended_baud_rate?: number | null
  recommended_serial_profile?: SerialProfile | null
  summary: string
}

type ProbeConfidence = {
  label: 'High' | 'Medium' | 'Low'
  ratioPct: number
  badgeClass: string
}

type ToastKind = 'success' | 'error' | 'info'

type ToastItem = {
  id: number
  message: string
  kind: ToastKind
  persistent?: boolean
}

type ViewKey = 'configuration' | 'live' | 'collections'
type LiveOrder = 'latest' | 'oldest'

export default function Home() {
  const [activeView, setActiveView] = useState<ViewKey>('configuration')
  const [connections, setConnections] = useState<ApiConnection[]>([])
  const [connectionsLoading, setConnectionsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [samples, setSamples] = useState<SensorSample[]>([])
  const [liveOrder, setLiveOrder] = useState<LiveOrder>(() => {
    if (typeof window === 'undefined') return 'latest'
    return (window.localStorage.getItem('as1100.liveOrder') as LiveOrder) || 'latest'
  })
  const [livePage, setLivePage] = useState(1)
  const [livePageSize, setLivePageSize] = useState<number>(() => {
    if (typeof window === 'undefined') return 50
    const saved = Number(window.localStorage.getItem('as1100.livePageSize'))
    return [10, 25, 50, 100, 250].includes(saved) ? saved : 50
  })
  const [connectionName, setConnectionName] = useState('')
  const [selectedPort, setSelectedPort] = useState('')
  const [activeConnections, setActiveConnections] = useState<ActiveConnection[]>([])
  const [frequency, setFrequency] = useState(10)
  const [baudRate, setBaudRate] = useState(19200)
  const [serialProfile, setSerialProfile] = useState<SerialProfile>('7E1')
  const [measuringMode, setMeasuringMode] = useState<'normal' | 'fast' | 'precise' | 'timed' | 'moving_target'>('normal')
  const [unit, setUnit] = useState('millimeters')
  const [decimalPlaces, setDecimalPlaces] = useState(4)
  const [rowsPerFile, setRowsPerFile] = useState(10000)
  const [, setLogs] = useState<string[]>([])
  const [, setPinnedEvents] = useState<string[]>([])
  const [muteNonErrorToasts, setMuteNonErrorToasts] = useState(false)
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const toastCounterRef = useRef(0)
  const wsRef = useRef<WebSocket | null>(null)
  const [sessionDirectory, setSessionDirectory] = useState('')
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyPageSize] = useState(10)
  const [historyTotalPages, setHistoryTotalPages] = useState(1)
  const [lastPortsRefresh, setLastPortsRefresh] = useState<Date | null>(null)
  const [serialRuntimeNote, setSerialRuntimeNote] = useState('')
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [probeRunning, setProbeRunning] = useState(false)
  const [probeResults, setProbeResults] = useState<RateProbeResponse[]>([])
  const [probeFailures, setProbeFailures] = useState<string[]>([])
  const [calibratedMaxHz, setCalibratedMaxHz] = useState<number | null>(null)
  const [doctorRunning, setDoctorRunning] = useState(false)
  const [doctorResult, setDoctorResult] = useState<ConnectionDoctorResponse | null>(null)
  const [persistedSampleCount, setPersistedSampleCount] = useState<number | null>(null)
  const lastPortCountRef = useRef<number | null>(null)

  const activeSessionConnections = useMemo(
    () => activeConnections.filter((conn) => conn.active),
    [activeConnections],
  )

  const orderedLiveSamples = useMemo(() => {
    if (liveOrder === 'latest') {
      return [...samples].reverse()
    }
    return samples
  }, [samples, liveOrder])

  const liveTotalPages = Math.max(1, Math.ceil(orderedLiveSamples.length / livePageSize))

  const staticMaxHz = useMemo(() => {
    const baudMax = Number(capabilities?.baud_max_hz?.[String(baudRate)] ?? (baudRate === 115200 ? 100 : baudRate === 9600 ? 10 : 20))
    const modeMax = Number(capabilities?.measuring_mode_max_hz?.[measuringMode] ?? (measuringMode === 'precise' ? 10 : measuringMode === 'normal' ? 20 : 100))
    return Math.min(baudMax, modeMax)
  }, [baudRate, measuringMode, capabilities])

  const effectiveMaxHz = useMemo(() => {
    if (calibratedMaxHz == null) return staticMaxHz
    return Math.min(staticMaxHz, calibratedMaxHz)
  }, [staticMaxHz, calibratedMaxHz])

  const supportedFrequencyOptions = useMemo(() => {
    const presets = capabilities?.frequency_presets_hz ?? [1, 2, 5, 10, 20, 50, 100]
    const filtered = presets.filter((hz) => hz <= effectiveMaxHz)
    return filtered.length > 0 ? filtered : [Math.max(1, Math.floor(effectiveMaxHz))]
  }, [capabilities, effectiveMaxHz])

  const paginatedLiveSamples = useMemo(() => {
    const start = (livePage - 1) * livePageSize
    return orderedLiveSamples.slice(start, start + livePageSize)
  }, [orderedLiveSamples, livePage, livePageSize])

  const timestampZoneLabel = useMemo(() => {
    const tzName = systemInfo?.timestamp_timezone_name?.trim()
    const offsetLabel = systemInfo?.timestamp_utc_offset_label?.trim()

    if (tzName && offsetLabel) return `${tzName} (${offsetLabel})`
    if (offsetLabel) return offsetLabel
    if (tzName) return tzName
    return 'Host local time'
  }, [systemInfo?.timestamp_timezone_name, systemInfo?.timestamp_utc_offset_label])

  useEffect(() => {
    if (livePage > liveTotalPages) {
      setLivePage(liveTotalPages)
    }
  }, [livePage, liveTotalPages])

  useEffect(() => {
    if (frequency > effectiveMaxHz) {
      setFrequency(supportedFrequencyOptions[supportedFrequencyOptions.length - 1])
    }
  }, [effectiveMaxHz, frequency, supportedFrequencyOptions])

  useEffect(() => {
    setProbeResults([])
    setProbeFailures([])
    setCalibratedMaxHz(null)
    setDoctorResult(null)
  }, [selectedPort, baudRate, serialProfile, measuringMode])

  useEffect(() => {
    void fetchConnections()
    void fetchHistory(1)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const saved = window.localStorage.getItem('as1100.muteNonErrorToasts')
    if (saved === '1') {
      setMuteNonErrorToasts(true)
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem('as1100.muteNonErrorToasts', muteNonErrorToasts ? '1' : '0')
  }, [muteNonErrorToasts])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem('as1100.liveOrder', liveOrder)
  }, [liveOrder])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem('as1100.livePageSize', String(livePageSize))
  }, [livePageSize])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const tag = target?.tagName?.toLowerCase() || ''
      const typing = tag === 'input' || tag === 'textarea' || tag === 'select' || target?.isContentEditable
      if (typing) return

      const key = event.key.toLowerCase()
      if (key === '1' || key === 'c') setActiveView('configuration')
      if (key === '2' || key === 'l') setActiveView('live')
      if (key === '3' || key === 'h') setActiveView('collections')
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    const refreshPorts = window.setInterval(() => {
      void fetchConnections({ silent: true })
    }, 8000)
    return () => window.clearInterval(refreshPorts)
  }, [])

  const addLog = (message: string) => {
    const stamp = new Date().toLocaleTimeString()
    const line = `[${stamp}] ${message}`
    setLogs((prev) => [line, ...prev].slice(0, 100))

    if (/(error|failed|stopped|disconnected)/i.test(message)) {
      setPinnedEvents((prev) => {
        const next = [line, ...prev.filter((p) => p !== line)]
        return next.slice(0, 8)
      })
    }
  }

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  const pushToast = (
    message: string,
    kind: ToastKind = 'info',
    options?: { persistent?: boolean },
  ) => {
    if (muteNonErrorToasts && kind !== 'error') {
      return null
    }

    toastCounterRef.current += 1
    const id = toastCounterRef.current
    const persistent = options?.persistent ?? false
    setToasts((prev) => [...prev, { id, message, kind, persistent }])
    if (!persistent) {
      window.setTimeout(() => {
        removeToast(id)
      }, 3500)
    }
    return id
  }

  const fetchConnections = async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false
    if (!silent) {
      setConnectionsLoading(true)
    }
    try {
      const [response, infoResponse, capabilitiesResponse] = await Promise.all([
        axios.get<ApiConnection[]>(`${API_URL}/api/connections`),
        axios.get<SystemInfo>(`${API_URL}/api/system-info`),
        axios.get<Capabilities>(`${API_URL}/api/capabilities`),
      ])

      const info = infoResponse.data
      setConnections((prev) => {
        const same =
          prev.length === response.data.length &&
          prev.every((p, i) => p.port === response.data[i]?.port && p.description === response.data[i]?.description)
        return same ? prev : response.data
      })
      setSystemInfo(info)
      setCapabilities(capabilitiesResponse.data)
      setLastPortsRefresh(new Date())
      if (lastPortCountRef.current !== response.data.length) {
        addLog(`Detected ${response.data.length} serial port(s)`)
        lastPortCountRef.current = response.data.length
      }

      const note = info.serial_note?.trim() || ''
      const shouldNotify =
        Boolean(note) &&
        (
          note !== serialRuntimeNote ||
          (info.sensor_provider === 'agent' && info.agent_reachable === false)
        )

      if (response.data.length === 0 || (info.sensor_provider === 'agent' && info.agent_reachable === false)) {
        setSerialRuntimeNote(note)
        if (shouldNotify) {
          addLog(note)
          pushToast(note, 'info')
        }
      } else {
        setSerialRuntimeNote('')
      }
    } catch (error) {
      console.error('Error fetching connections:', error)
      addLog('Failed to fetch COM ports from backend')
      pushToast('Could not load COM ports', 'error')
    } finally {
      if (!silent) {
        setConnectionsLoading(false)
      }
    }
  }

  const fetchHistory = async (page: number) => {
    setHistoryLoading(true)
    try {
      const response = await axios.get<{
        items: HistoryItem[]
        page: number
        total_pages: number
      }>(`${API_URL}/api/history`, {
        params: { page, page_size: historyPageSize },
      })
      setHistoryItems(response.data.items)
      setHistoryPage(response.data.page)
      setHistoryTotalPages(Math.max(1, response.data.total_pages))
    } catch (error) {
      console.error('Error fetching history:', error)
      addLog('Failed to fetch collection history')
      pushToast('Could not load collection history', 'error')
    } finally {
      setHistoryLoading(false)
    }
  }

  const parseIsoTimestamp = (timestamp?: string) => {
    if (!timestamp) return null

    const match = timestamp.trim().match(
      /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.(\d{1,6}))?(?:([+-]\d{2}:\d{2}|Z))?$/
    )

    if (!match) return null

    const [, datePart, timePart, , fractionDigits = '', offsetPart = ''] = match
    const milliseconds = fractionDigits ? fractionDigits.slice(0, 3).padEnd(3, '0') : ''

    return {
      datePart,
      timePart,
      milliseconds,
      offsetPart,
    }
  }

  const formatTimestampWithMs = (timestamp?: string) => {
    if (!timestamp) return '-'

    const parts = parseIsoTimestamp(timestamp)
    if (parts) {
      return parts.milliseconds
        ? `${parts.timePart}.${parts.milliseconds}`
        : parts.timePart
    }

    const timeOnly = timestamp.split('T')[1] || timestamp
    return timeOnly.replace(/([+-]\d{2}:\d{2}|Z)$/i, '').slice(0, 12)
  }

  const formatDateTime = (timestamp: string) => {
    const parts = parseIsoTimestamp(timestamp)
    if (parts) {
      const timeWithMs = parts.milliseconds
        ? `${parts.timePart}.${parts.milliseconds}`
        : parts.timePart
      return `${parts.datePart} ${timeWithMs}`
    }

    const d = new Date(timestamp)
    if (Number.isNaN(d.getTime())) return timestamp
    return d.toLocaleString()
  }

  const formatSize = (bytes: number) => `${(bytes / 1024).toFixed(2)} KB`

  const getProbeConfidence = (result: RateProbeResult): ProbeConfidence => {
    const ratio = result.target_hz > 0 ? result.achieved_hz / result.target_hz : 0
    const ratioPct = Math.round(ratio * 100)

    if (ratio >= 0.9) {
      return {
        label: 'High',
        ratioPct,
        badgeClass: 'border-emerald-300 bg-emerald-50 text-emerald-700',
      }
    }
    if (ratio >= 0.75) {
      return {
        label: 'Medium',
        ratioPct,
        badgeClass: 'border-amber-300 bg-amber-50 text-amber-700',
      }
    }
    return {
      label: 'Low',
      ratioPct,
      badgeClass: 'border-rose-300 bg-rose-50 text-rose-700',
    }
  }

  const handleAddConnection = () => {
    const port = selectedPort.trim()
    if (!port) {
      addLog('Choose a detected port')
      return
    }

    if (activeConnections.some((conn) => conn.port.toLowerCase() === port.toLowerCase())) {
      addLog(`Connection ${port} is already added`)
      return
    }

    const newConn: ActiveConnection = {
      port,
      name: connectionName.trim() || `Connection ${activeConnections.length + 1}`,
      active: true,
      status: 'Ready',
    }

    setActiveConnections((prev) => [...prev, newConn])
    setConnectionName('')
    addLog(`Added ${newConn.name} (${newConn.port})`)
    pushToast(`Added ${newConn.name}`, 'success')
  }

  const handleToggleConnection = (index: number) => {
    setActiveConnections((prev) =>
      prev.map((conn, i) => (i === index ? { ...conn, active: !conn.active } : conn)),
    )
  }

  const handleRemoveConnection = (index: number) => {
    const removed = activeConnections[index]
    setActiveConnections((prev) => prev.filter((_, i) => i !== index))
    addLog(`Removed ${removed.name} (${removed.port})`)
    pushToast(`Removed ${removed.name}`, 'info')
  }

  const connectWebSocket = (sid: string) => {
    wsRef.current?.close()
    const wsUrl = API_URL.replace('http://', 'ws://').replace('https://', 'wss://') + `/ws/sessions/${sid}`
    const ws = new WebSocket(wsUrl)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as { type?: string; timestamp?: string; values?: Record<string, string> }
      if (data.type === 'sample') {
        setSamples((prev) => [...prev, { timestamp: data.timestamp, values: data.values }])
      }
    }

    ws.onopen = () => addLog('Live stream connected')
    ws.onerror = () => addLog('WebSocket error while streaming live data')
    ws.onclose = () => addLog('Live stream disconnected')

    wsRef.current = ws
  }

  const createAndStartSession = async () => {
    if (activeSessionConnections.length === 0) {
      addLog('Please enable at least one active connection')
      return
    }

    const loadingToastId = pushToast('Starting collection session...', 'info', { persistent: true })

    try {
      const response = await axios.post<{ session_id: string }>(`${API_URL}/api/sessions`, {
        connections: activeSessionConnections.map(({ port, name, active }) => ({ port, name, active })),
        frequency_hz: frequency,
        baud_rate: baudRate,
        serial_profile: serialProfile,
        measuring_mode: measuringMode,
        unit,
        decimal_places: decimalPlaces,
        export_csv: true,
        rows_per_file: rowsPerFile,
      })

      const newSessionId = response.data.session_id
      setSessionId(newSessionId)
      setSamples([])
      setPersistedSampleCount(null)
      setLivePage(1)

      await axios.post(`${API_URL}/api/sessions/${newSessionId}/start`)
      setIsRunning(true)
      setActiveConnections((prev) =>
        prev.map((conn) => ({
          ...conn,
          status: conn.active ? 'Collecting' : conn.status,
        })),
      )
      connectWebSocket(newSessionId)
      addLog(`Session ${newSessionId} started`)
      pushToast(`Session ${newSessionId} started`, 'success')
    } catch (error) {
      console.error('Error starting collection:', error)
      addLog('Failed to start session')
      pushToast('Failed to start session', 'error')
    } finally {
      if (loadingToastId !== null) {
        removeToast(loadingToastId)
      }
    }
  }

  const runRateProbe = async () => {
    const activePorts = Array.from(
      new Set(
        activeConnections
          .filter((conn) => conn.active)
          .map((conn) => conn.port.trim())
          .filter(Boolean),
      ),
    )

    const portsToProbe = activePorts.length > 0
      ? activePorts
      : [selectedPort.trim()].filter(Boolean)

    if (portsToProbe.length === 0) {
      addLog('Select or add at least one active port before running calibration')
      pushToast('Select at least one active port first', 'error')
      return
    }

    setProbeRunning(true)
    setProbeFailures([])
    const loadingToastId = pushToast(
      `Calibrating ${portsToProbe.length} port(s): ${portsToProbe.join(', ')}`,
      'info',
      { persistent: true },
    )

    try {
      const successful: RateProbeResponse[] = []
      const failures: string[] = []

      for (const port of portsToProbe) {
        try {
          const response = await axios.post<RateProbeResponse>(`${API_URL}/api/capabilities/probe-rate`, {
            port,
            baud_rate: baudRate,
            serial_profile: serialProfile,
            measuring_mode: measuringMode,
            duration_seconds: 2.5,
          })
          successful.push(response.data)
          addLog(`Calibration complete on ${port}: recommended max ${response.data.recommended_max_hz} Hz`)
        } catch (error) {
          console.error(`Calibration failed on ${port}:`, error)
          const detail = axios.isAxiosError(error)
            ? (error.response?.data as { detail?: string })?.detail || error.message
            : 'Unknown error'
          const msg = `${port}: ${detail}`
          failures.push(msg)
          addLog(`Calibration failed on ${msg}`)
        }
      }

      setProbeResults(successful)
      setProbeFailures(failures)

      if (successful.length > 0) {
        const aggregatedMax = Math.min(...successful.map((r) => r.recommended_max_hz))
        setCalibratedMaxHz(aggregatedMax)
        pushToast(
          `Calibration complete for ${successful.length}/${portsToProbe.length} port(s). Applied max: ${aggregatedMax} Hz`,
          failures.length > 0 ? 'info' : 'success',
        )
      } else {
        setCalibratedMaxHz(null)
        pushToast('Calibration failed on all selected ports', 'error')
      }
    } finally {
      setProbeRunning(false)
      if (loadingToastId !== null) removeToast(loadingToastId)
    }
  }

  const runConnectionDoctor = async () => {
    const port = selectedPort.trim()
    if (!port) {
      addLog('Select a detected port before running Connection Doctor')
      pushToast('Select a port first', 'error')
      return
    }

    setDoctorRunning(true)
    setDoctorResult(null)
    const loadingToastId = pushToast(`Diagnosing ${port} serial settings...`, 'info', { persistent: true })

    try {
      const response = await axios.post<ConnectionDoctorResponse>(`${API_URL}/api/connections/doctor`, {
        port,
        sensor_id: 0,
        current_baud_rate: baudRate,
        current_serial_profile: serialProfile,
      })

      setDoctorResult(response.data)
      addLog(`Connection Doctor: ${response.data.summary}`)

      const recBaud = response.data.recommended_baud_rate
      const recProfile = response.data.recommended_serial_profile
      if (recBaud != null && recProfile != null && (recBaud !== baudRate || recProfile !== serialProfile)) {
        pushToast(`Doctor recommends ${recBaud}/${recProfile} for ${port}`, 'info')
      } else {
        pushToast('Connection Doctor completed', 'success')
      }
    } catch (error) {
      console.error('Connection Doctor failed:', error)
      const detail = axios.isAxiosError(error)
        ? (error.response?.data as { detail?: string })?.detail || error.message
        : 'Unknown error'
      const statusCode = axios.isAxiosError(error) ? error.response?.status : undefined
      const message = statusCode === 404
        ? 'Connection Doctor endpoint not found on backend. Restart backend services to load latest API changes.'
        : detail
      addLog(`Connection Doctor failed: ${message}`)
      pushToast(statusCode === 404 ? 'Connection Doctor unavailable until backend restart' : 'Connection Doctor failed', 'error')
    } finally {
      setDoctorRunning(false)
      if (loadingToastId !== null) removeToast(loadingToastId)
    }
  }

  const handleStartCollection = async () => {
    await createAndStartSession()
    setActiveView('live')
  }

  const handleStopCollection = async () => {
    if (!sessionId) return

    const loadingToastId = pushToast('Stopping collection session...', 'info', { persistent: true })

    try {
      const response = await axios.post<{
        session_directory?: string
        total_samples?: number
        total_samples_persisted?: number
      }>(`${API_URL}/api/sessions/${sessionId}/stop`)
      setIsRunning(false)
      setActiveConnections((prev) => prev.map((conn) => ({ ...conn, status: 'Stopped' })))
      wsRef.current?.close()
      setSessionDirectory(response.data.session_directory || '')
      if (typeof response.data.total_samples_persisted === 'number') {
        setPersistedSampleCount(response.data.total_samples_persisted)
      } else if (typeof response.data.total_samples === 'number') {
        setPersistedSampleCount(response.data.total_samples)
      }
      await fetchHistory(1)
      addLog(`Session ${sessionId} stopped`)
      pushToast(`Session ${sessionId} stopped`, 'info')
    } catch (error) {
      console.error('Error stopping collection:', error)
      addLog('Failed to stop session')
      pushToast('Failed to stop session', 'error')
    } finally {
      if (loadingToastId !== null) {
        removeToast(loadingToastId)
      }
    }
  }

  const downloadHistorySession = async (historySessionId: string) => {
    const loadingToastId = pushToast(`Preparing ${historySessionId} download...`, 'info', { persistent: true })
    try {
      const response = await axios.get<{ csv_data: string; filename: string }>(
        `${API_URL}/api/history/${historySessionId}/download`
      )
      const csv = response.data.csv_data
      const element = document.createElement('a')
      element.setAttribute('href', `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`)
      element.setAttribute('download', response.data.filename)
      element.style.display = 'none'
      document.body.appendChild(element)
      element.click()
      document.body.removeChild(element)
      addLog(`Downloaded collection ${historySessionId}`)
      pushToast(`Downloaded ${historySessionId}`, 'success')
    } catch (error) {
      console.error(`Error downloading collection ${historySessionId}:`, error)
      addLog(`Failed to download collection ${historySessionId}`)
      pushToast(`Failed to download ${historySessionId}`, 'error')
    } finally {
      if (loadingToastId !== null) {
        removeToast(loadingToastId)
      }
    }
  }

  const downloadHistorySessionParts = async (historySessionId: string) => {
    const loadingToastId = pushToast(`Preparing ${historySessionId} ZIP...`, 'info', { persistent: true })
    try {
      const response = await axios.get<BlobPart>(
        `${API_URL}/api/history/${historySessionId}/download-parts`,
        { responseType: 'blob' },
      )
      const blob = new Blob([response.data], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const contentDisposition = String(response.headers['content-disposition'] || '')
      const headerFilenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
      const downloadFilename = headerFilenameMatch?.[1] || `session_${historySessionId}_parts.zip`
      const element = document.createElement('a')
      element.setAttribute('href', url)
      element.setAttribute('download', downloadFilename)
      element.style.display = 'none'
      document.body.appendChild(element)
      element.click()
      document.body.removeChild(element)
      window.URL.revokeObjectURL(url)
      addLog(`Downloaded ZIP parts for ${historySessionId}`)
      pushToast(`Downloaded ${historySessionId} parts ZIP`, 'success')
    } catch (error) {
      console.error(`Error downloading ZIP parts for ${historySessionId}:`, error)
      addLog(`Failed to download ZIP parts for ${historySessionId}`)
      pushToast(`Failed to download parts for ${historySessionId}`, 'error')
    } finally {
      if (loadingToastId !== null) {
        removeToast(loadingToastId)
      }
    }
  }

  const deleteHistorySession = async (historySessionId: string) => {
    if (!window.confirm(`Permanently delete collection ${historySessionId} and all its data?`)) return
    const loadingToastId = pushToast(`Deleting ${historySessionId}...`, 'info', { persistent: true })
    try {
      await axios.delete(`${API_URL}/api/history/${historySessionId}`)
      addLog(`Deleted collection ${historySessionId}`)
      pushToast(`Deleted ${historySessionId}`, 'success')
      await fetchHistory(historyPage)
    } catch (error) {
      console.error(`Error deleting collection ${historySessionId}:`, error)
      addLog(`Failed to delete collection ${historySessionId}`)
      pushToast(`Failed to delete ${historySessionId}`, 'error')
    } finally {
      if (loadingToastId !== null) {
        removeToast(loadingToastId)
      }
    }
  }

  const navItems: Array<{ key: ViewKey; label: string }> = [
    { key: 'configuration', label: 'Configuration' },
    { key: 'live', label: 'Live Data' },
    { key: 'collections', label: 'Collections' },
  ]

  const renderAgentStatusBanner = () => {
    if (systemInfo?.sensor_provider !== 'agent' || systemInfo?.agent_reachable !== false) {
      return null
    }

    const reason = systemInfo.agent_reason?.trim() || 'unknown reason'
    return (
      <div className="mt-3 rounded-md border border-rose-300 bg-rose-50 p-3 text-xs text-rose-700">
        <p className="font-semibold">Host Agent Offline</p>
        <p className="mt-1 text-rose-600">
          Backend is configured for host-agent mode, but cannot reach the agent.
        </p>
        <p className="mt-1 text-rose-600">Reason: {reason}</p>
        <button
          onClick={() => {
            const hint = 'Start it with start_hybrid.bat (or run host_agent/main.py via uvicorn on port 8010).'
            addLog(hint)
            pushToast(hint, 'info')
          }}
          className="mt-2 rounded bg-rose-600 px-2 py-1 text-[11px] font-semibold text-white hover:bg-rose-500"
        >
          How to start agent
        </button>
      </div>
    )
  }

  const getTopAgentStatus = () => {
    if (systemInfo?.sensor_provider !== 'agent') {
      return {
        label: 'Provider: direct',
        dotClass: 'bg-slate-500',
        textClass: 'text-slate-700',
      }
    }

    if (systemInfo.agent_reachable === true) {
      return {
        label: 'Agent Online',
        dotClass: 'animate-pulse bg-emerald-500',
        textClass: 'text-emerald-700',
      }
    }

    if (systemInfo.agent_reachable === false) {
      return {
        label: 'Agent Offline',
        dotClass: 'bg-rose-500',
        textClass: 'text-rose-700',
      }
    }

    return {
      label: 'Agent Unknown',
      dotClass: 'bg-amber-400',
      textClass: 'text-amber-700',
    }
  }

  const renderConfiguration = () => (
    <section className="mx-auto w-full max-w-6xl space-y-5">
      <h2 className="text-lg font-semibold text-cyan-700">Configuration</h2>

      <div className="mt-4 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Sensor Configuration</h3>
          <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div>
              <label className="text-sm text-slate-700">Detected Port</label>
              <select
                value={selectedPort}
                onChange={(e) => setSelectedPort(e.target.value)}
                className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
              >
                <option value="">-- Select a port --</option>
                {connections.map((conn) => (
                  <option key={conn.port} value={conn.port}>
                    {conn.port} {conn.description ? `(${conn.description})` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm text-slate-700">Connection Name</label>
              <input
                type="text"
                value={connectionName}
                onChange={(e) => setConnectionName(e.target.value)}
                placeholder="e.g., Sensor A"
                className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
              />
            </div>

            <div className="lg:col-span-2 grid grid-cols-2 gap-2">
              <button
                onClick={handleAddConnection}
                className="rounded-md bg-cyan-600 px-4 py-2 font-medium text-white hover:bg-cyan-500"
              >
                Add Connection
              </button>
              <button
                onClick={() => { void fetchConnections() }}
                className="rounded-md bg-slate-700 px-4 py-2 font-medium text-white hover:bg-slate-600"
              >
                Refresh Ports
              </button>
            </div>
          </div>

          {connectionsLoading ? (
            <div className="mt-4 animate-pulse rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
              Loading connections...
            </div>
          ) : activeConnections.length > 0 ? (
            <div className="mt-4 overflow-hidden rounded-md border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-100 text-slate-700">
                  <tr>
                    <th className="px-2 py-2 text-left">Active</th>
                    <th className="px-2 py-2 text-left">Name</th>
                    <th className="px-2 py-2 text-left">Port</th>
                    <th className="px-2 py-2 text-left">Status</th>
                    <th className="px-2 py-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {activeConnections.map((conn, idx) => (
                    <tr key={`${conn.port}`} className="border-t border-slate-200">
                      <td className="px-2 py-2">
                        <input type="checkbox" checked={conn.active} onChange={() => handleToggleConnection(idx)} />
                      </td>
                      <td className="px-2 py-2">{conn.name}</td>
                      <td className="px-2 py-2">{conn.port}</td>
                      <td className="px-2 py-2">{conn.status}</td>
                      <td className="px-2 py-2 text-right">
                        <button
                          onClick={() => handleRemoveConnection(idx)}
                          className="rounded bg-rose-600 px-2 py-1 text-xs font-medium text-white hover:bg-rose-500"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="mt-4 rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
              No active connections yet. Add a connection to begin.
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 pt-4">
          <h3 className="text-sm font-semibold text-slate-800">Measurement Settings</h3>
          <div className="mt-3 space-y-3">
          <div>
            <label className="text-sm text-slate-700">Baud Rate</label>
            <select
              value={baudRate}
              onChange={(e) => setBaudRate(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            >
              {(capabilities?.supported_baud_rates ?? [9600, 19200, 115200]).map((baud) => (
                <option key={baud} value={baud}>{baud}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm text-slate-700">Serial Profile</label>
            <select
              value={serialProfile}
              onChange={(e) => setSerialProfile(e.target.value as SerialProfile)}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            >
              {(capabilities?.supported_serial_profiles ?? ['7E1', '8N1']).map((profile) => (
                <option key={profile} value={profile}>{profile}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Use the sensor&apos;s configured framing (manual: s#br). Common default is 7E1.
            </p>
          </div>

          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm text-slate-800">Connection Doctor (Port/Serial Settings)</p>
                <p className="text-xs text-slate-500">Tests serial combinations and recommends the best baud/profile for the selected port.</p>
              </div>
              <button
                onClick={() => { void runConnectionDoctor() }}
                disabled={doctorRunning}
                className="rounded bg-cyan-700 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-600 disabled:opacity-50"
              >
                {doctorRunning ? 'Diagnosing...' : 'Diagnose Connection'}
              </button>
            </div>

            {doctorResult && (
              <div className="mt-3 space-y-2 text-xs">
                <p className="text-slate-700">{doctorResult.summary}</p>

                {doctorResult.recommended_baud_rate != null && doctorResult.recommended_serial_profile != null && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded border border-emerald-700 bg-emerald-900/30 px-2 py-1 text-emerald-200">
                      Recommended: {doctorResult.recommended_baud_rate} / {doctorResult.recommended_serial_profile}
                    </span>
                    <button
                      onClick={() => {
                        if (doctorResult.recommended_baud_rate != null) {
                          setBaudRate(doctorResult.recommended_baud_rate)
                        }
                        if (doctorResult.recommended_serial_profile != null) {
                          setSerialProfile(doctorResult.recommended_serial_profile)
                        }
                        addLog(`Applied Connection Doctor recommendation: ${doctorResult.recommended_baud_rate}/${doctorResult.recommended_serial_profile}`)
                        pushToast('Applied doctor recommendation', 'success')
                      }}
                      className="rounded bg-emerald-700 px-2 py-1 text-[11px] font-semibold text-white hover:bg-emerald-600"
                    >
                      Apply Recommendation
                    </button>
                  </div>
                )}

                {doctorResult.attempted.length > 0 && (
                  <ul className="max-h-28 space-y-1 overflow-auto rounded border border-slate-200 bg-white p-2 text-slate-700">
                    {doctorResult.attempted.map((attempt, idx) => (
                      <li key={`${attempt.baud_rate}-${attempt.serial_profile}-${idx}`}>
                        {attempt.success ? '✓' : '•'} {attempt.baud_rate}/{attempt.serial_profile}
                        {attempt.detail ? ` — ${attempt.detail}` : ''}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="text-sm text-slate-700">Measuring Mode</label>
            <select
              value={measuringMode}
              onChange={(e) => setMeasuringMode(e.target.value as 'normal' | 'fast' | 'precise' | 'timed' | 'moving_target')}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            >
              <option value="normal">Normal (max 20 Hz)</option>
              <option value="fast">Fast (max 100 Hz)</option>
              <option value="precise">Precise (max 10 Hz)</option>
              <option value="timed">Timed (up to 100 Hz)</option>
              <option value="moving_target">Moving Target (max 100 Hz)</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-slate-700">Frequency (Hz)</label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(Number(e.target.value))}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            >
              {supportedFrequencyOptions.map((hz) => (
                <option key={hz} value={hz}>{hz}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Allowed by selected baud + mode: up to {staticMaxHz} Hz
              {calibratedMaxHz != null ? ` • Calibrated max: ${calibratedMaxHz} Hz` : ''}
            </p>
          </div>

          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm text-slate-800">Runtime Rate Calibration (Throughput)</p>
                <p className="text-xs text-slate-500">Measures achievable sample rate on selected ports using current serial settings + mode.</p>
              </div>
              <button
                onClick={() => { void runRateProbe() }}
                disabled={probeRunning}
                className="rounded bg-indigo-700 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
              >
                {probeRunning ? 'Calibrating...' : 'Calibrate Rate'}
              </button>
            </div>
            {probeFailures.length > 0 && (
              <div className="mt-3 rounded border border-rose-800 bg-rose-950/30 p-2 text-xs text-rose-200">
                <p className="font-semibold">Calibration failures</p>
                <ul className="mt-1 list-disc pl-4">
                  {probeFailures.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
            )}

            {probeResults.length > 0 && (
              <div className="mt-3 space-y-3">
                <p className="text-[11px] text-slate-500">
                  Confidence uses achieved/target ratio per row (High ≥ 90%, Medium ≥ 75%, Low &lt; 75%).
                  Coverage is samples received vs samples expected for that target and duration.
                </p>
                {probeResults.map((result) => (
                  <div key={result.port} className="overflow-x-auto rounded border border-slate-200 bg-white p-2">
                    <p className="mb-2 text-xs text-slate-700">
                      Port {result.port} • Recommended max: {result.recommended_max_hz} Hz
                    </p>
                    <table className="min-w-full text-xs">
                      <thead className="text-slate-700">
                        <tr>
                          <th className="px-2 py-1 text-left">Target Hz</th>
                          <th className="px-2 py-1 text-left">Achieved Hz</th>
                          <th className="px-2 py-1 text-left">Samples</th>
                          <th className="px-2 py-1 text-left">Expected</th>
                          <th className="px-2 py-1 text-left">Coverage</th>
                          <th className="px-2 py-1 text-left">Confidence</th>
                          <th className="px-2 py-1 text-left">Stable</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.results.map((r) => {
                          const confidence = getProbeConfidence(r)
                          const expectedSamples = Math.max(1, Math.round(r.target_hz * r.duration_seconds))
                          const coveragePct = Math.round((r.samples / expectedSamples) * 100)
                          return (
                            <tr key={`${result.port}-${r.target_hz}`} className="border-t border-slate-200 text-slate-700">
                              <td className="px-2 py-1">{r.target_hz}</td>
                              <td className="px-2 py-1">{r.achieved_hz}</td>
                              <td className="px-2 py-1">{r.samples}</td>
                              <td className="px-2 py-1">{expectedSamples}</td>
                              <td className="px-2 py-1">{coveragePct}%</td>
                              <td className="px-2 py-1">
                                <span className={`inline-flex rounded border px-2 py-0.5 ${confidence.badgeClass}`}>
                                  {confidence.label} ({confidence.ratioPct}%)
                                </span>
                              </td>
                              <td className="px-2 py-1">{r.stable ? 'Yes' : 'No'}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="text-sm text-slate-700">Unit</label>
            <select 
              value={unit} 
              onChange={(e) => setUnit(e.target.value)} 
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            >
              <option value="millimeters">Millimeters</option>
              <option value="centimeters">Centimeters</option>
              <option value="meters">Meters</option>
              <option value="feet">Feet</option>
              <option value="inches">Inches</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-slate-700">Decimal Places</label>
            <input 
              type="number" 
              value={decimalPlaces} 
              onChange={(e) => setDecimalPlaces(Number(e.target.value))} 
              min={1} 
              max={10} 
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2" 
            />
          </div>

          <div>
            <label className="text-sm text-slate-700">Max Rows/File</label>
            <input
              type="number"
              value={rowsPerFile}
              onChange={(e) => setRowsPerFile(Number(e.target.value))}
              min={1000}
              step={1000}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            />
            <p className="mt-1 text-xs text-slate-500">CSV files are created in containers when this row limit is reached. Default: 10,000 rows.</p>
          </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
          <p>Data is automatically persisted in backend containers.</p>
          {sessionDirectory && (
            <p className="mt-1">Last output: {sessionDirectory}</p>
          )}
        </div>
      </div>
    </section>
  )

  const renderLiveData = () => (
    <section className="mx-auto w-full max-w-6xl space-y-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-cyan-700">Live Data Stream</h2>
        <div className="flex items-center gap-2">
          <span className={`rounded px-3 py-1 text-xs font-semibold ${isRunning ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'}`}>
            {isRunning ? 'Collecting' : 'Idle'}
          </span>
          <span className="rounded bg-slate-100 px-3 py-1 text-sm text-slate-700">Samples: {samples.length}</span>
        </div>
      </div>

      <div className="mb-3 grid grid-cols-1 gap-2 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700 md:grid-cols-3">
        <label className="flex items-center gap-2">
          <span>Order</span>
          <select
            value={liveOrder}
            onChange={(e) => {
              setLiveOrder(e.target.value as LiveOrder)
              setLivePage(1)
            }}
            className="rounded border border-slate-300 bg-white px-2 py-1"
          >
            <option value="latest">Latest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </label>

        <label className="flex items-center gap-2">
          <span>Rows/Page</span>
          <select
            value={livePageSize}
            onChange={(e) => {
              setLivePageSize(Number(e.target.value))
              setLivePage(1)
            }}
            className="rounded border border-slate-300 bg-white px-2 py-1"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={250}>250</option>
          </select>
        </label>

        <div className="flex items-center justify-between md:justify-end gap-2">
          <button
            onClick={() => setLivePage((prev) => Math.max(1, prev - 1))}
            disabled={livePage <= 1 || samples.length === 0}
            className="rounded bg-slate-700 px-3 py-1 text-white hover:bg-slate-600 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-slate-600 whitespace-nowrap">Page</span>
          <input
            type="number"
            min={1}
            max={liveTotalPages}
            value={livePage}
            disabled={samples.length === 0}
            onChange={(e) => {
              const v = Number(e.target.value)
              if (!Number.isNaN(v)) setLivePage(Math.max(1, Math.min(liveTotalPages, v)))
            }}
            className="w-14 rounded border border-slate-300 bg-white px-2 py-1 text-center text-slate-700 disabled:opacity-50"
          />
          <span className="text-slate-600 whitespace-nowrap">/ {liveTotalPages}</span>
          <button
            onClick={() => setLivePage((prev) => Math.min(liveTotalPages, prev + 1))}
            disabled={livePage >= liveTotalPages || samples.length === 0}
            className="rounded bg-slate-700 px-3 py-1 text-white hover:bg-slate-600 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

      {samples.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left">
                  <div>Timestamp</div>
                  <div className="text-[10px] font-normal text-slate-500">{timestampZoneLabel}</div>
                </th>
                {activeSessionConnections.map((conn) => (
                  <th key={conn.port} className="px-3 py-2 text-left">
                    {conn.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedLiveSamples.map((sample, idx) => (
                <tr key={`${sample.timestamp ?? 'sample'}-${(livePage - 1) * livePageSize + idx}`} className="border-b border-slate-200">
                  <td className="px-3 py-2">{formatTimestampWithMs(sample.timestamp)}</td>
                  {activeSessionConnections.map((conn) => (
                    <td key={conn.port} className="px-3 py-2">
                      {sample.values?.[conn.name] || '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
          <p className="text-sm text-slate-700">No live samples yet.</p>
          <p className="mt-1 text-xs text-slate-500">Start a collection from Configuration to begin streaming.</p>
          <button
            onClick={() => setActiveView('configuration')}
            className="mt-4 rounded bg-cyan-700 px-3 py-1 text-xs font-medium text-white hover:bg-cyan-600"
          >
            Go To Configuration
          </button>
        </div>
      )}
    </section>
  )

  const renderCollections = () => (
    <section className="mx-auto w-full max-w-6xl space-y-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-cyan-700">Collections</h2>
        <button
          onClick={() => { void fetchHistory(historyPage) }}
          className="rounded bg-slate-700 px-3 py-1 text-xs font-medium text-white hover:bg-slate-600"
        >
          Refresh
        </button>
      </div>

      {historyLoading ? (
        <div className="space-y-2">
          <div className="h-10 animate-pulse rounded bg-slate-100" />
          <div className="h-10 animate-pulse rounded bg-slate-100" />
          <div className="h-10 animate-pulse rounded bg-slate-100" />
        </div>
      ) : historyItems.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left">Session ID</th>
                <th className="px-3 py-2 text-left">Files</th>
                <th className="px-3 py-2 text-left">Size</th>
                <th className="px-3 py-2 text-left">
                  <div>Last Updated</div>
                  <div className="text-[10px] font-normal text-slate-500">{timestampZoneLabel}</div>
                </th>
                <th className="px-3 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {historyItems.map((item) => (
                <tr key={item.session_id} className="border-b border-slate-200">
                  <td className="px-3 py-2 font-mono text-xs">{item.session_id}</td>
                  <td className="px-3 py-2">{item.file_count}</td>
                  <td className="px-3 py-2">{formatSize(item.total_size_bytes)}</td>
                  <td className="px-3 py-2">{formatDateTime(item.last_updated)}</td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => { void downloadHistorySession(item.session_id) }}
                        className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-500"
                      >
                        Download CSV
                      </button>
                      <button
                        onClick={() => { void downloadHistorySessionParts(item.session_id) }}
                        className="rounded bg-cyan-700 px-3 py-1 text-xs font-medium text-white hover:bg-cyan-600"
                      >
                        Download ZIP
                      </button>
                      <button
                        onClick={() => { void deleteHistorySession(item.session_id) }}
                        className="rounded bg-rose-700 px-3 py-1 text-xs font-medium text-white hover:bg-rose-600"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
          <p className="text-sm text-slate-700">No historical collections found yet.</p>
          <p className="mt-1 text-xs text-slate-500">Run and stop a collection to have it appear here.</p>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
        <span>Page {historyPage} of {historyTotalPages}</span>
        <div className="flex gap-2">
          <button
            onClick={() => { if (historyPage > 1) { void fetchHistory(historyPage - 1) } }}
            disabled={historyPage <= 1}
            className="rounded bg-slate-700 px-3 py-1 text-white hover:bg-slate-600 disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => { if (historyPage < historyTotalPages) { void fetchHistory(historyPage + 1) } }}
            disabled={historyPage >= historyTotalPages}
            className="rounded bg-slate-700 px-3 py-1 text-white hover:bg-slate-600 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </section>
  )

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-20 w-64 overflow-y-auto border-r border-slate-200 bg-white p-3">
        <div className="rounded-xl bg-gradient-to-r from-cyan-100 to-emerald-100 p-4">
          <h1 className="text-lg font-semibold tracking-tight">AS1100 Collector</h1>
          <p className="mt-1 text-xs text-slate-600">Capture, stream, and manage collections</p>
        </div>
        <nav className="mt-4 space-y-2">
          {navItems.map((item) => (
            <button
              key={item.key}
              onClick={() => setActiveView(item.key)}
              className={`w-full cursor-pointer rounded-xl border px-4 py-2.5 text-left transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
                activeView === item.key
                  ? 'border-cyan-300 bg-cyan-50'
                  : 'border-slate-200 bg-white hover:bg-slate-50'
              }`}
            >
              <p className="font-semibold">{item.label}</p>
            </button>
          ))}
        </nav>

        <div className="mt-6 space-y-2">
          <p className="text-xs text-slate-600 font-semibold">Collection Control</p>
          <button 
            onClick={handleStartCollection} 
            disabled={isRunning || activeSessionConnections.length === 0}
            className="w-full cursor-pointer rounded-xl border border-emerald-600 bg-emerald-600 px-4 py-2.5 font-semibold text-white transition-colors duration-200 hover:bg-emerald-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Start Collection
          </button>
          <button 
            onClick={handleStopCollection} 
            disabled={!sessionId}
            className="w-full cursor-pointer rounded-xl border border-rose-600 bg-rose-600 px-4 py-2.5 font-semibold text-white transition-colors duration-200 hover:bg-rose-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Stop Collection
          </button>
        </div>
      </aside>

      <div className="ml-64 flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="px-4 py-3 md:px-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-cyan-700">System Status</h2>
              <div className="flex items-start gap-3">
                <div className="space-y-1 rounded border border-slate-200 bg-slate-50 px-2 py-1">
                  <div className="flex items-center gap-2">
                    <div className={`h-2.5 w-2.5 rounded-full ${getTopAgentStatus().dotClass}`} />
                    <span className={`text-xs font-semibold ${getTopAgentStatus().textClass}`}>
                      {getTopAgentStatus().label}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-600">
                    Provider: {systemInfo?.sensor_provider ?? 'unknown'} • Ports: {connections.length} • Last refresh: {lastPortsRefresh ? lastPortsRefresh.toLocaleTimeString() : 'n/a'}
                  </p>
                </div>
                {sessionId && (
                  <span className="rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700">
                    Session: {sessionId.slice(0, 8)}...
                  </span>
                )}
                <button
                  onClick={() => setMuteNonErrorToasts((prev) => !prev)}
                  className="cursor-pointer rounded bg-slate-700 px-2 py-1 text-[11px] text-white transition-colors duration-200 hover:bg-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                >
                  {muteNonErrorToasts ? 'Unmute' : 'Mute'}
                </button>
              </div>
            </div>

            {renderAgentStatusBanner()}

            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white p-2">
                <p className="text-[11px] text-slate-600">Detected COM Ports</p>
                <p className="mt-1 text-lg font-semibold text-cyan-700">{connections.length}</p>
                <p className="text-[10px] text-slate-600">
                  {connectionsLoading
                    ? 'Refreshing...'
                    : lastPortsRefresh
                      ? 'Port scan active'
                      : 'Scanning ports...'}
                </p>
                {connections.length === 0 && serialRuntimeNote && (
                  <p className="mt-1 text-[10px] text-amber-700">{serialRuntimeNote}</p>
                )}
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-2">
                <p className="text-[11px] text-slate-600">Current Job</p>
                <p className="mt-1 text-lg font-semibold text-emerald-700">
                  {isRunning ? 'Collecting' : sessionId ? 'Stopped' : 'Not started'}
                </p>
                {sessionId && (
                  <p className="text-[10px] font-mono text-slate-600">ID: {sessionId}</p>
                )}
                <p className="text-[10px] text-slate-600">Active connections: {activeSessionConnections.length}</p>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-2">
                <p className="text-[11px] text-slate-600">Sensor Stream</p>
                <p className="mt-1 text-lg font-semibold text-indigo-700">{samples.length}</p>
                {persistedSampleCount != null && !isRunning && (
                  <p className="text-[10px] text-emerald-700">Persisted rows: {persistedSampleCount}</p>
                )}
                <p className="text-[10px] text-slate-600">
                  Last sample: {formatTimestampWithMs(samples[samples.length - 1]?.timestamp)} {timestampZoneLabel}
                </p>
                {isRunning && (
                  <p className="mt-1 text-[10px] text-emerald-700">
                    Target rate: {frequency} Hz @ {baudRate}
                  </p>
                )}
              </div>
            </div>
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-auto p-4 md:p-6">
          {activeView === 'configuration' && renderConfiguration()}
          {activeView === 'live' && renderLiveData()}
          {activeView === 'collections' && renderCollections()}
        </main>

        <div className="pointer-events-none fixed right-4 top-4 z-30 flex w-80 flex-col gap-2">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`pointer-events-auto rounded-lg border px-3 py-2 text-sm shadow-lg backdrop-blur ${{
                success: 'border-emerald-300 bg-emerald-50 text-emerald-700',
                error: 'border-rose-300 bg-rose-50 text-rose-700',
                info: 'border-cyan-300 bg-cyan-50 text-cyan-800',
              }[toast.kind]}`}
            >
              <div className="flex items-start justify-between gap-2">
                <span>{toast.message}</span>
                <button
                  onClick={() => removeToast(toast.id)}
                  className="rounded bg-black/20 px-1 text-xs text-white hover:bg-black/30"
                  aria-label="Dismiss notification"
                >
                  x
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
