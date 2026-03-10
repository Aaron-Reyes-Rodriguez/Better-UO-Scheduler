import FileUploader from './components/FileUploader'
import Box from '@mui/material/Box'
import Container from '@mui/material/Container'
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import HowToVideo from '../assets/HowToVideo.mp4'

export default function Scheduler() {
    return (
        <Container maxWidth="md" sx={{ mt: { xs: 4, md: 8 }, mb: 4 }}>
            <Box sx={{ textAlign: 'center', mb: 6 }}>
                <Typography 
                    variant="h3" 
                    component="h1" 
                    gutterBottom
                    sx={{ fontWeight: 800, color: 'text.primary', letterSpacing: '-0.5px' }}
                >
                    Upload Your Transcript
                </Typography>
                <Typography variant="h6" color="text.secondary" paragraph sx={{ maxWidth: '600px', mx: 'auto', lineHeight: 1.6 }}>
                    Get started by uploading your recent Ducks On Track transcript.
                </Typography>
                <video src={HowToVideo} controls style={{ width: '100%', maxWidth: '600px', borderRadius: '8px' }}>
                    Your browser does not support the video tag.
                </video>
            </Box>

            <Paper 
                elevation={3} 
                sx={{ 
                    p: { xs: 3, md: 6 }, 
                    borderRadius: 3, 
                    bgcolor: '#1e293b', 
                    border: '1px solid #334155',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 3
                }}
            >
                <Box 
                    sx={{ 
                        width: 80, 
                        height: 80, 
                        borderRadius: '50%', 
                        bgcolor: '#0f172a', 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        mb: 2,
                        border: '1px solid #334155'
                    }}
                >
                    <UploadFileIcon sx={{ fontSize: 40, color: '#646cff' }} />
                </Box>
                
                <Typography variant="h5" sx={{ color: 'white', fontWeight: 600 }}>
                    Select your Ducks On Track PDF File
                </Typography>
                
                <Box sx={{ width: '100%', maxWidth: '400px', mt: 2 }}>
                    <FileUploader/>
                </Box>
                
                <Typography variant="body2" sx={{ color: '#94a3b8', mt: 3, textAlign: 'center' }}>
                    Supported formats: PDF only
                </Typography>
            </Paper>
        </Container>
    );
}
