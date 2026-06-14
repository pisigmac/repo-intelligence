import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

export function Dashboard() {
  const [pets, setPets] = useState([]);

  useEffect(() => {
    supabase.from('pets').select('*').then(({ data }) => {
      if (data) setPets(data);
    });
  }, []);

  return (
    <div>
      <h1>DevPet Dashboard</h1>
      <ul>
        {pets.map((pet: any) => (
          <li key={pet.id}>{pet.name}</li>
        ))}
      </ul>
    </div>
  );
}

export default Dashboard;
