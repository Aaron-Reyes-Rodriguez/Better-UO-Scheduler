import { Link } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';

export default function Navbar() {
    return (
        <AppBar position="static" sx={{ bgcolor: '#1e293b', boxShadow: 3 }}>
            <Toolbar sx={{ justifyContent: 'space-between' }}>
                <Typography
                    variant="h5"
                    component={Link}
                    to="/"
                    sx={{
                        textDecoration: 'none',
                        color: 'inherit',
                        fontWeight: 700,
                        letterSpacing: 1,
                    }}
                >
                    Quackademics
                </Typography>
                
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button 
                        color="inherit" 
                        component={Link} 
                        to="/search"
                        sx={{ fontWeight: 600, textTransform: 'none', fontSize: '1rem' }}
                    >
                        Search
                    </Button>
                    <Button 
                        color="inherit" 
                        component={Link} 
                        to="/scheduler"
                        sx={{ fontWeight: 600, textTransform: 'none', fontSize: '1rem' }}
                    >
                        Upload Transcript
                    </Button>
                </Box>
            </Toolbar>
        </AppBar>
    );
}