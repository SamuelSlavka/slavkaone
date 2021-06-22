import React, { useState, useLayoutEffect } from 'react';
import { serverAddr } from './constants';

const Home = () => {
  const [transaction, setTransaction] = useState('');
  // fetches last transaction trought server from blockhain
  async function fetchMyAPI() {
    const response = await fetch(`${serverAddr}/api/`);
    const blocks = await response.json();
    setTransaction(JSON.stringify(blocks, null, 2));
  }

  useLayoutEffect(() => {
    fetchMyAPI();
  }, []);

  return (
    <div className="home">
      <h2>Latest transaction on ETH:</h2>
      <br />
      <pre>{transaction}</pre>
    </div>
  );
};

export default Home;