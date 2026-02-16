import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, type Mocked } from 'vitest';
import App from './App';
import axios from 'axios';

// Mock axios
vi.mock('axios');
const mockedAxios = axios as Mocked<typeof axios>;

describe('App Component', () => {
  it('renders initial greeting', () => {
    render(<App />);
    expect(screen.getByText(/Hello! I am your data assistant/i)).toBeInTheDocument();
  });

  it('shows login button when no token', () => {
    // Ensure no token in localStorage
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    render(<App />);
    expect(screen.getByText(/Sign In/i)).toBeInTheDocument();
  });

  it('sends message and displays response', async () => {
    // Mock token
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('fake-token');
    
    // Mock API response
    mockedAxios.post.mockResolvedValueOnce({
      data: {
        conversation_id: '123',
        chunks: [{ simple: { text: 'Here is your answer' } }]
      }
    });

    render(<App />);
    
    // Type in input
    const input = screen.getByPlaceholderText(/Ask a question/i);
    fireEvent.change(input, { target: { value: 'How many users?' } });
    
    // Click send
    const sendButton = screen.getByRole('button', { name: '' }); // Send button has no text, just icon
    fireEvent.click(sendButton);

    // Expect loading state or optimistic update
    expect(screen.getByText(/How many users\?/i)).toBeInTheDocument();

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText(/Here is your answer/i)).toBeInTheDocument();
    });
  });
});
