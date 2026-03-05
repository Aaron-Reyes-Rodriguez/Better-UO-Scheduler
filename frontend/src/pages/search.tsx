import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { suggestClasses, suggestProfessors } from '../api';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import SearchIcon from '@mui/icons-material/Search';

type SearchType = 'class' | 'professor';

export default function Search() {
  const navigate = useNavigate();
  const [searchType, setSearchType] = useState<SearchType>('class');
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);

  const goToResult = (value: string) => {
    const path = searchType === 'class' ? '/class' : '/professor';
    navigate(`${path}?q=${encodeURIComponent(value)}`);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    goToResult(trimmed);
  };

  useEffect(() => {
    let cancelled = false;
    const q = query.trim();
    if (!q) {
      setSuggestions([]);
      setActiveIndex(-1);
      return;
    }

    const timer = setTimeout(async () => {
      const results =
        searchType === 'class'
          ? await suggestClasses(q, 8)
          : await suggestProfessors(q, 8);
      if (!cancelled) {
        setSuggestions(results);
        setActiveIndex(results.length > 0 ? 0 : -1);
      }
    }, 120);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, searchType]);

  return (
    <Container
      maxWidth="sm"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        pt: { xs: 10, md: 16 },
      }}
    >
      {/* Title */}
      <Typography
        variant="h2"
        component="h1"
        sx={{
          fontWeight: 800,
          color: '#00010dff',
          letterSpacing: '-0.5px',
          mb: 1,
        }}
      >
        Search
      </Typography>

      <Typography
        variant="body1"
        sx={{ color: '#94a3b8', mb: 4 }}
      >
        Search by course or professor
      </Typography>

      {/* Toggle */}
      <ToggleButtonGroup
        value={searchType}
        exclusive
        onChange={(_e, val) => {
          if (val) setSearchType(val as SearchType);
        }}
        sx={{
          mb: 2.5,
          '& .MuiToggleButton-root': {
            color: '#64748b',
            borderColor: '#e2e8f0',
            textTransform: 'none',
            fontWeight: 600,
            fontSize: '0.9rem',
            px: 3,
            py: 0.8,
            '&.Mui-selected': {
              bgcolor: '#f1f5f9',
              color: '#1e293b',
              borderColor: '#cbd5e1',
              '&:hover': { bgcolor: '#e2e8f0' },
            },
            '&:hover': { bgcolor: '#f8fafc' },
          },
        }}
      >
        <ToggleButton value="class">Class</ToggleButton>
        <ToggleButton value="professor">Professor</ToggleButton>
      </ToggleButtonGroup>

      {/* Search form */}
      <Box
        component="form"
        onSubmit={onSubmit}
        sx={{ width: '100%', position: 'relative' }}
      >
        <TextField
          fullWidth
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (suggestions.length === 0) return;
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setActiveIndex((i) => (i + 1) % suggestions.length);
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              setActiveIndex(
                (i) => (i - 1 + suggestions.length) % suggestions.length
              );
            } else if (
              e.key === 'Enter' &&
              activeIndex >= 0 &&
              activeIndex < suggestions.length
            ) {
              e.preventDefault();
              const value = suggestions[activeIndex];
              setQuery(value);
              goToResult(value);
            }
          }}
          placeholder={
            searchType === 'class' ? 'e.g. CS 110' : 'e.g. Pat Holleran'
          }
          variant="outlined"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ color: '#94a3b8' }} />
              </InputAdornment>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: '#fff',
              borderRadius: '999px',
              fontSize: '1.15rem',
              py: 0.5,
              '& fieldset': { borderColor: '#e2e8f0' },
              '&:hover fieldset': { borderColor: '#cbd5e1' },
              '&.Mui-focused fieldset': { borderColor: '#94a3b8' },
            },
          }}
        />

        {/* Autocomplete dropdown */}
        {suggestions.length > 0 && (
          <Box
            sx={{
              position: 'absolute',
              zIndex: 20,
              top: 'calc(100% + 4px)',
              left: 0,
              right: 0,
              borderRadius: 2,
              bgcolor: '#fff',
              border: '1px solid #e2e8f0',
              maxHeight: 280,
              overflowY: 'auto',
              boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
            }}
          >
            {suggestions.map((item, idx) => (
              <Box
                key={`${item}-${idx}`}
                component="button"
                type="button"
                onMouseDown={(e: React.MouseEvent) => {
                  e.preventDefault();
                  setQuery(item);
                  goToResult(item);
                }}
                sx={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  border: 'none',
                  borderBottom:
                    idx === suggestions.length - 1
                      ? 'none'
                      : '1px solid #f1f5f9',
                  borderRadius: 0,
                  py: 1.2,
                  px: 2,
                  bgcolor:
                    idx === activeIndex ? '#f1f5f9' : 'transparent',
                  color: '#1e293b',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  fontFamily: 'inherit',
                  transition: 'background-color 0.12s',
                  '&:hover': { bgcolor: '#f8fafc' },
                }}
              >
                {item}
              </Box>
            ))}
          </Box>
        )}
      </Box>
    </Container>
  );
}
