import { createFileRoute } from '@tanstack/react-router';
import Chatbot from '../page/chatbot';

export const Route = createFileRoute('/chatbot')({
  component: Chatbot,
});