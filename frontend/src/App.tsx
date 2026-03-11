/**
 * @file App.tsx
 * @description Root landing page component for the Quackademics
 *   (Better-UO-Scheduler) React frontend. Renders the home screen with
 *   navigation buttons to the Search and Scheduler (Upload Transcript) pages.
 * @authors Aaron Reyes-Rodriguez
 *
 * System: Better-UO-Scheduler (Quackademics)
 *   This component is mounted by main.tsx inside a React Router context and
 *   displayed at the root path "/".
 */

// React Router Link: renders an accessible anchor that navigates within the SPA.
import { Link } from 'react-router-dom'
// Material UI components used for layout and typography on the landing page.
import Box from '@mui/material/Box'
import Container from '@mui/material/Container'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
// Material UI icons used as visual cues on the navigation buttons.
import SearchIcon from '@mui/icons-material/Search'
import UploadFileIcon from '@mui/icons-material/UploadFile'
// import HealthCheck from './pages/components/HealthCheck'

/**
 * App – root landing-page component.
 *
 * Displays the Quackademics welcome screen with two primary call-to-action
 * buttons: one that navigates to the Search page and one for the transcript
 * upload (Scheduler) page.
 *
 * @returns JSX element representing the home page.
 */
function App() {
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

      {/* <HealthCheck /> */}
    </Container>
  )
}

export default App

