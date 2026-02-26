import { useState } from 'react'
import { fetchHealth } from '../../api'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart'

export default function HealthCheck() {
  const [health, setHealth] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function checkBackend() {
    setError(null)
    setHealth(null)
    setLoading(true)
    try {
      const data = await fetchHealth()
      setHealth(JSON.stringify(data, null, 2))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Paper elevation={3} sx={{ p: 4, borderRadius: 3, bgcolor: '#1e293b', border: '1px solid #334155' }}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, color: 'white' }}>
        <MonitorHeartIcon sx={{ color: '#94a3b8' }} /> API Status
      </Typography>
      <Typography variant="body2" sx={{ mb: 3, color: '#cbd5e1' }}>
        Click below to check if the backend service is running and accessible.
      </Typography>
      
      <Button 
          onClick={checkBackend} 
          disabled={loading}
          variant="contained"
          sx={{ mb: 2, bgcolor: '#475569', '&:hover': { bgcolor: '#334155' } }}
      >
        {loading ? 'Checking...' : 'Check API Health'}
      </Button>

      {error && (
          <Typography color="error" variant="body2" sx={{ mt: 2 }}>
              {error}
          </Typography>
      )}
      
      {health && (
          <Box 
              sx={{ 
                  mt: 3, 
                  p: 2, 
                  bgcolor: '#0f172a', 
                  borderRadius: 2, 
                  textAlign: 'left',
                  overflowX: 'auto'
              }}
          >
              <Typography component="pre" variant="body2" sx={{ m: 0, color: '#38bdf8', fontFamily: 'monospace' }}>
                  {health}
              </Typography>
          </Box>
      )}
    </Paper>
  )
}
