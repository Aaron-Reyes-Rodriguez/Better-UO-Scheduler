/**
 * @file navbar.tsx
 * @description Top navigation bar component for Quackademics
 *   (Better-UO-Scheduler). Displays the application name as a home link and
 *   navigation buttons for the Search and Upload Transcript pages.
 * @authors Aaron Reyes-Rodriguez
 *
 * System: Better-UO-Scheduler (Quackademics)
 *   Rendered by Layout.tsx so it appears at the top of every page.
 */

// React Router Link: enables client-side navigation without a page reload.
import { Link } from 'react-router-dom';
// Material UI app-bar and layout components.
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';

/**
 * Navbar – application top navigation bar.
 *
 * Renders a fixed application bar with the Quackademics brand name
 * (links to home) and navigation buttons for Search and Upload Transcript.
 *
 * @returns JSX element representing the top navigation bar.
 */
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