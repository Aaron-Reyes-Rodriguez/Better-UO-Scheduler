import { useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchHealth } from './api'
import Box from '@mui/material/Box'
import Container from '@mui/material/Container'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import Paper from '@mui/material/Paper'
import SearchIcon from '@mui/icons-material/Search'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart'

function App() {
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
    <Container maxWidth="md" sx={{ mt: { xs: 4, md: 10 }, mb: 4, textAlign: 'center' }}>
      <Box sx={{ mb: 8 }}>
        <Typography 
            variant="h2" 
            component="h1" 
            gutterBottom
            sx={{ fontWeight: 800, color: 'text.primary', letterSpacing: '-0.5px' }}
        >
          Welcome to <Box component="span" sx={{ color: '#646cff' }}>Quackademics</Box>
        </Typography>
        <Typography variant="h6" color="text.secondary" paragraph sx={{ maxWidth: '600px', mx: 'auto', lineHeight: 1.6 }}>
          Your ultimate tool for picking classes! Upload your transcript to get personalized degree info, or search for classes and professors.
        </Typography>
      </Box>

      <Stack 
        direction={{ xs: 'column', sm: 'row' }} 
        spacing={3} 
        justifyContent="center"
        sx={{ mb: 10 }}
      >
        <Button
          component={Link}
          to="/search"
          variant="contained"
          size="large"
          startIcon={<SearchIcon />}
          sx={{ py: 1.5, px: 4, fontSize: '1.1rem', borderRadius: 2, bgcolor: '#646cff', '&:hover': { bgcolor: '#535bf2' } }}
        >
          Search Classes & Professors
        </Button>
        <Button
          component={Link}
          to="/scheduler"
          variant="outlined"
          size="large"
          startIcon={<UploadFileIcon />}
          sx={{ py: 1.5, px: 4, fontSize: '1.1rem', borderRadius: 2, borderWidth: 2, '&:hover': { borderWidth: 2 } }}
        >
          Upload Transcript
        </Button>
      </Stack>

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
    </Container>
  )
}

export default App
