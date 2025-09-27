// Import necessary libraries

import React, { useState, useEffect, useCallback } from 'react';
import background from './background.jpg'; // Assuming background.jpg is in src folder

// --- Login Component ---
function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError("");
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:5000/login", { // Ensure URL is correct
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        const data = await response.json();
        onLoginSuccess(data.token); // Pass token up
      } else {
        const errorData = await response.json();
        setLoginError(errorData.error || `Login failed (Status: ${response.status})`);
      }
    } catch (error) {
      console.error("Login API error:", error);
      setLoginError("Login request failed. Is the backend running?");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        backgroundImage: `url(${background})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        minHeight: "100vh", // Use minHeight for flexibility
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        color: "#fff",
        textShadow: "1px 1px 4px #000",
        padding: "20px", // Add padding for smaller screens
      }}
    >
      <h1 style={{ fontSize: "clamp(1.8em, 5vw, 2.5em)", marginBottom: "10px", textAlign: "center" }}>
        GenAI for Traffic Simulations Management
      </h1>
      <p style={{ marginBottom: "30px", textAlign: "center", fontSize: "clamp(0.8em, 2vw, 1em)" }}>
        Peacock Braden, Pandey Prakhar, Curran Cameron, Villacortes Justine, David Zhan
      </p>

      <div
        style={{
          backgroundColor: "rgba(255, 255, 255, 0.9)",
          color: "#000",
          padding: "30px",
          borderRadius: "10px",
          boxShadow: "0 4px 10px rgba(0, 0, 0, 0.3)",
          width: "clamp(280px, 80%, 350px)", // Responsive width
          textAlign: "center",
        }}
      >
        <h2>Login</h2>
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: "15px" }}>
            <input
              type="text"
              placeholder="Username (admin)" // Hint for demo
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "10px", // Increased padding
                borderRadius: "5px",
                border: "1px solid #ccc",
                boxSizing: 'border-box', // Include padding in width
              }}
            />
          </div>
          <div style={{ marginBottom: "20px" }}> {/* Increased margin */}
            <input
              type="password"
              placeholder="Password (password)" // Hint for demo
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "5px",
                border: "1px solid #ccc",
                boxSizing: 'border-box',
              }}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            style={{
              padding: "12px 20px", // Increased padding
              backgroundColor: "#007BFF",
              color: "#fff",
              border: "none",
              borderRadius: "5px",
              cursor: "pointer",
              width: "100%",
              fontSize: "1em",
              opacity: isLoading ? 0.7 : 1,
            }}
          >
            {isLoading ? "Logging in..." : "Login"}
          </button>
        </form>
        {loginError && <p style={{ color: "red", marginTop: "15px", fontWeight: "bold" }}>{loginError}</p>}
      </div>
    </div>
  );
}


// --- File Upload Component ---
function FileUpload({ onUploadComplete }) {
  const [inputFiles, setInputFiles] = useState([]); // Use array for multiple files
  const [exeFile, setExeFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState({ message: "", error: false });
  const [isLoading, setIsLoading] = useState(false);

  const handleInputFilesChange = (e) => {
    setInputFiles(e.target.files); // Store FileList directly
    setUploadStatus({ message: "", error: false }); // Clear status on new selection
  };

  const handleExeFileChange = (e) => {
    setExeFile(e.target.files[0]); // Only one exe file
    setUploadStatus({ message: "", error: false }); // Clear status
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (inputFiles.length === 0) {
        setUploadStatus({ message: "Please select at least one input file.", error: true });
        return;
    }

    const formData = new FormData();
    // Append all selected input files
    for (let i = 0; i < inputFiles.length; i++) {
      formData.append("input_file", inputFiles[i]);
    }
    // Append exe file if selected
    if (exeFile) {
      formData.append("exe", exeFile);
    }

    setIsLoading(true);
    setUploadStatus({ message: "Uploading...", error: false });

    try {
      const response = await fetch("http://localhost:5000/upload", { // Ensure URL is correct
        method: "POST",
        body: formData, // No 'Content-Type' header needed for FormData
      });
      const data = await response.json();
      if (response.ok) {
        setUploadStatus({ message: data.message || "Upload successful!", error: false });
        onUploadComplete(data); // Pass the backend response { input_files: [...paths], exe_used: path }
         // Optionally clear file inputs after successful upload
         // document.getElementById('input-files-input').value = null;
         // document.getElementById('exe-file-input').value = null;
         setInputFiles([]);
         setExeFile(null);
      } else {
        setUploadStatus({ message: data.error || `Upload failed (Status: ${response.status})`, error: true });
        onUploadComplete(null); // Signal upload failure
      }
    } catch (error) {
      console.error("Upload API error:", error);
      setUploadStatus({ message: "Upload request failed. Is the backend running?", error: true });
      onUploadComplete(null); // Signal upload failure
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.tabContent}>
      <h2>Upload Simulation Files</h2>
      <form onSubmit={handleSubmit}>
        <div style={styles.formGroup}>
          <label htmlFor="input-files-input" style={styles.label}>Input Files (.txt, .csv, .json, .xml, .int, .dat, .out):</label>
          <input
            id="input-files-input"
            type="file"
            multiple // Allow multiple file selection
            onChange={handleInputFilesChange}
            required // Make sure at least one file is selected
            style={styles.input}
           />
           {inputFiles.length > 0 && <span style={styles.fileInfo}>{inputFiles.length} file(s) selected</span>}
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="exe-file-input" style={styles.label}>Integrats Executable (.exe) (Optional - Uses default if none provided):</label>
          <input
            id="exe-file-input"
            type="file"
            accept=".exe" // Hint to browser for allowed type
            onChange={handleExeFileChange}
            style={styles.input}
           />
           {exeFile && <span style={styles.fileInfo}>{exeFile.name} selected</span>}
        </div>
        <button type="submit" disabled={isLoading} style={styles.button}>
          {isLoading ? "Uploading..." : "Upload Files"}
        </button>
      </form>
       {uploadStatus.message && (
         <p style={{ color: uploadStatus.error ? 'red' : 'green', marginTop: '15px', fontWeight: 'bold' }}>
           {uploadStatus.message}
         </p>
       )}
    </div>
  );
}


// --- Simulation Run Component ---
function SimulationRun({ uploadedData }) {
  const [metadata, setMetadata] = useState(""); // Use string for simple metadata
  const [runStatus, setRunStatus] = useState("");
  const [runId, setRunId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSampleLoading, setIsSampleLoading] = useState(false); // Separate loading state for sample
  const [sampleOutput, setSampleOutput] = useState(""); // State for sample output
  const [sampleErrorDetails, setSampleErrorDetails] = useState(""); // State for sample error

  // Clear results when uploaded data changes (new upload)
  useEffect(() => {
      setRunStatus("");
      setRunId(null);
      setSampleOutput("");
      setSampleErrorDetails("");
      setMetadata(""); // Reset metadata field too
  }, [uploadedData]);


  const handleCustomSubmit = async (e) => {
    e.preventDefault();
    if (!uploadedData || !uploadedData.input_files || !uploadedData.exe_used) {
      setRunStatus("Upload error: Missing file data. Please upload files again.");
      return;
    }

    setRunId(null); // Reset run ID from previous runs
    setSampleOutput(""); // Clear previous sample output
    setSampleErrorDetails(""); // Clear previous sample error
    setRunStatus("Running custom simulation...");
    setIsLoading(true);

    const payload = {
      input_files: uploadedData.input_files, // Should be list of paths from backend
      exe_used: uploadedData.exe_used, // Should be path from backend
      metadata: metadata ? { description: metadata } : {}, // Send as object if not empty
    };

    try {
      const response = await fetch("http://localhost:5000/simulate", { // Ensure URL is correct
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      setRunId(data.run_id || null); // Store run_id even on failure if provided

      if (response.ok) {
        setRunStatus(`Custom simulation completed. Run ID: ${data.run_id}`);
      } else {
        setRunStatus(`Custom simulation failed: ${data.error || 'Unknown error'}. ${data.details ? 'Details below.' : ''}`);
        setSampleErrorDetails(data.details || `Error ${response.status}`); // Show details in error area
      }
    } catch (error) {
      console.error("Custom Simulate API error:", error);
      setRunStatus("Error during custom simulation request: Is the backend running?");
      setSampleErrorDetails(error.toString());
    } finally {
      setIsLoading(false);
    }
  };

  const handleSampleRun = async () => {
    setRunStatus("Running sample simulation...");
    setRunId(null); // Reset run ID
    setSampleOutput(""); // Clear previous output
    setSampleErrorDetails(""); // Clear previous error
    setIsSampleLoading(true);
    try {
      const response = await fetch("http://localhost:5000/run_sample", { // Ensure URL is correct
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}), // Empty body is fine as per backend
      });
      const data = await response.json();
      setRunId(data.run_id || null); // Store run_id regardless of success/failure

      if (response.ok) {
        setRunStatus(`Sample simulation completed successfully! Run ID: ${data.run_id}`);
        setSampleOutput(data.output || "[No output content received]"); // Store the output
        console.log("Sample output received:", data.output);
      } else {
        setRunStatus(`Sample simulation failed: ${data.error || "Unknown error"}. Run ID: ${data.run_id || 'N/A'}`);
        setSampleErrorDetails(data.details || `Error ${response.status}`); // Store error details
        console.error("Sample run error details:", data.details);
      }
    } catch (error) {
      console.error("Sample Run API error:", error);
      setRunStatus("Error running sample simulation request: Is the backend running?");
      setSampleErrorDetails("Frontend request failed: " + error.toString());
    } finally {
      setIsSampleLoading(false);
    }
  };

  // Determine if custom run button should be disabled
  const isCustomRunDisabled = isLoading || isSampleLoading || !uploadedData;

  return (
    <div style={styles.tabContent}>
      <h2>Run Simulation</h2>

      {/* Custom Simulation Section */}
      <form onSubmit={handleCustomSubmit}>
         <p>Run simulation with the files uploaded in the 'Upload Files' tab.</p>
        <div style={styles.formGroup}>
          <label htmlFor="metadata-input" style={styles.label}>Metadata/Description (Optional):</label>
          <input
             id="metadata-input"
            type="text"
            value={metadata}
            onChange={(e) => setMetadata(e.target.value)}
            placeholder="e.g., Morning peak test run"
            style={styles.input}
            disabled={!uploadedData} // Disable if no files uploaded
          />
        </div>
        <button type="submit" disabled={isCustomRunDisabled} style={styles.button}>
          {isLoading ? "Running..." : "Run Custom Simulation"}
        </button>
         { !uploadedData && <p style={{color: 'orange', marginTop: '5px'}}>Upload files first to enable custom run.</p>}
      </form>

      <hr style={styles.hr} />

      {/* Sample Simulation Section */}
      <h3>Run Sample Simulation</h3>
      <p>Runs the built-in sample using 'intgrats.exe' and 'INET_I.INET' located on the server.</p>
      <button onClick={handleSampleRun} disabled={isLoading || isSampleLoading} style={styles.button}>
        {isSampleLoading ? "Running Sample..." : "Run Sample Simulation"}
      </button>

      {/* Status and Results Display */}
       <div style={styles.resultsArea}>
         { (isLoading || isSampleLoading) && <p>Running...</p>}
         {runStatus && <p style={styles.statusMessage}>Status: {runStatus}</p>}

         {/* Display Run ID and Download Link */}
         {runId && (
           <div style={styles.downloadLink}>
             <p>Simulation Run ID: <strong>{runId}</strong></p>
             <a
               href={`http://localhost:5000/download/${runId}`} // Ensure URL is correct
               target="_blank"
               rel="noopener noreferrer"
               style={styles.link}
             >
               Download Run Archive (.zip)
             </a>
           </div>
         )}

         {/* Display Sample Output */}
         {sampleOutput && !sampleErrorDetails && ( // Only show output if no error
           <div style={styles.outputContainer}>
             <h4>Sample Simulation Output:</h4>
             <pre style={styles.preformattedText}>
               {sampleOutput}
             </pre>
           </div>
         )}

         {/* Display Sample/Custom Error Details */}
         {sampleErrorDetails && (
            <div style={styles.outputContainer}>
              <h4>Error Details:</h4>
              <pre style={{...styles.preformattedText, ...styles.errorText}}>
                {sampleErrorDetails}
              </pre>
            </div>
         )}
       </div>
    </div>
  );
}


// --- Runs List Component ---
function RunsList() {
  const [runs, setRuns] = useState([]);
  const [fetchError, setFetchError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const fetchRuns = useCallback(async () => {
      setIsLoading(true);
      setFetchError("");
      try {
          const response = await fetch("http://localhost:5000/runs"); // Ensure URL is correct
          if (!response.ok) {
              throw new Error(`Failed to fetch runs list (Status: ${response.status})`);
          }
          const data = await response.json();
          setRuns(data || []); // Ensure runs is always an array
      } catch (err) {
          console.error("Error fetching runs:", err);
          setFetchError("Failed to load runs list. Is the backend running?");
          setRuns([]); // Clear runs on error
      } finally {
          setIsLoading(false);
      }
  }, []); // No dependencies, fetch logic is self-contained

  // Fetch runs when component mounts
  useEffect(() => {
      fetchRuns();
  }, [fetchRuns]); // fetchRuns is stable due to useCallback


  const formatMetadata = (metadata) => {
      if (!metadata) return 'N/A';
      if (typeof metadata === 'string') {
          // Basic check if it *looks* like JSON before showing raw string
          if (metadata.startsWith('{') && metadata.endsWith('}')) {
              try {
                  // Try parsing for better display (e.g., description)
                  const parsed = JSON.parse(metadata);
                  return parsed.description || parsed.type || JSON.stringify(parsed); // Show description, type, or stringified
              } catch {
                   return metadata; // Show raw string if parsing fails
              }
          }
          return metadata; // Return raw string if not JSON-like
      }
      if (typeof metadata === 'object') {
          return metadata.description || metadata.type || JSON.stringify(metadata);
      }
      return String(metadata); // Fallback
  };

  return (
    <div style={styles.tabContent}>
      <h2>Previous Simulation Runs</h2>
      <button onClick={fetchRuns} disabled={isLoading} style={{...styles.button, marginBottom: '15px'}}>
          {isLoading ? "Refreshing..." : "Refresh List"}
      </button>
      {fetchError && <p style={{ color: "red", fontWeight: "bold" }}>{fetchError}</p>}
      {isLoading && runs.length === 0 && <p>Loading runs...</p>}
      {!isLoading && runs.length === 0 && !fetchError && <p>No simulation runs found.</p>}
      {runs.length > 0 && (
        <ul style={styles.list}>
          {runs.map((run) => (
            <li key={run.run_id} style={styles.listItem}>
               <div><strong>ID:</strong> {run.run_id}</div>
               <div><strong>Time:</strong> {run.timestamp ? new Date(run.timestamp).toLocaleString() : 'N/A'}</div>
               <div><strong>Exe:</strong> {run.exe_used || 'N/A'}</div>
               <div><strong>Status:</strong> {run.status || 'Unknown'}</div>
               <div><strong>Meta:</strong> {formatMetadata(run.metadata)}</div>
              <a
                href={`http://localhost:5000/download/${run.run_id}`} // Ensure URL is correct
                target="_blank"
                rel="noopener noreferrer"
                style={{...styles.link, marginTop: '5px', display: 'inline-block'}}
              >
                Download Archive
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


// --- LLM Chat Component ---
function LLMChat() {
  const [inputText, setInputText] = useState("");
  const [uploadedFile, setUploadedFile] = useState(null); // Store the uploaded file
  const [conversation, setConversation] = useState([]); // { sender: 'User'/'LLM', text: '...' }
  const [isLoading, setIsLoading] = useState(false);
  const chatBoxRef = React.useRef(null);

  // Scroll to the bottom of the chat box
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [conversation]);

  // Handle file selection
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setUploadedFile(file);
    setConversation((prev) => [...prev, { sender: "User", text: `File selected: ${file.name}` }]);
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isLoading) return;

    setIsLoading(true);
    let payload = { text: inputText.trim() };

    // If there is a file, read its content and add it to the payload
    if (uploadedFile) {
      const fileReader = new FileReader();
      fileReader.onload = async (event) => {
        const fileContent = event.target.result;
        payload.file_content = fileContent;
        payload.file_name = uploadedFile.name;

        // Add user message to the conversation
        const userMessage = { sender: "User", text: inputText || "Processing uploaded file..." };
        setConversation((prev) => [...prev, userMessage]);

        // Send request to the backend
        await sendToLLM(payload);
      };
      fileReader.readAsText(uploadedFile); // Assume the file is in text format
    } else if (inputText.trim()) {
      // If no file, send only the text
      const userMessage = { sender: "User", text: inputText };
      setConversation((prev) => [...prev, userMessage]);
      await sendToLLM(payload);
    } else {
      setIsLoading(false);
      return;
    }
  };

  // Send request to the backend
  const sendToLLM = async (payload) => {
    try {
      const response = await fetch("http://localhost:5000/llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `LLM request failed (Status: ${response.status})`);
      }
      const data = await response.json();
      const botMessage = { sender: "LLM", text: data.response || "[No response from LLM]" };
      setConversation((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("LLM API error:", error);
      const errorMessage = { sender: "LLM", text: `Error: ${error.message}` };
      setConversation((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setInputText(""); // Clear the input field
      setUploadedFile(null); // Clear the file selection
    }
  };

  return (
    <div style={styles.tabContent}>
      <h2>LLM Chat</h2>
      <p>Interact with the AI Assistant. Upload a file or type a query.</p>
      <div ref={chatBoxRef} style={styles.chatBox}>
      {conversation.map((msg, index) =>
        msg.sender === "User" ? (
          <p key={index} style={styles.userMessage}>
            <strong>{msg.sender}:</strong> {msg.text}
          </p>
        ) : (
          <pre key={index} style={{ ...styles.llmMessage, whiteSpace: "pre-wrap", fontFamily: "monospace" }}>
            <strong>{msg.sender}:</strong> {msg.text}
          </pre>
        )
      )}
        {isLoading && <p style={styles.llmMessage}><em>LLM thinking...</em></p>}
      </div>
      <form onSubmit={handleSubmit} style={styles.chatForm}>
        <input
          type="text"
          placeholder="Type your query..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={isLoading}
          style={styles.chatInput}
        />
        <input
          type="file"
          onChange={handleFileChange}
          disabled={isLoading}
          style={{ marginLeft: '10px' }}
        />
        <button type="submit" disabled={isLoading || (!inputText.trim() && !uploadedFile)} style={styles.chatButton}>
          Send
        </button>
      </form>
    </div>
  );
}


// --- Main Application Component (Tabs) ---
function MainApp({ onLogout }) {
  const [uploadedData, setUploadedData] = useState(null); // Holds { input_files: [...paths], exe_used: path }
  const [activeTab, setActiveTab] = useState("upload"); // Default tab

  const handleUploadComplete = useCallback((data) => {
      setUploadedData(data);
      if (data) {
          // Optionally switch to simulate tab after successful upload
          // setActiveTab("simulate");
      }
  }, []); // Empty dependency array as it only uses setUploadedData

  const renderTab = () => {
    switch (activeTab) {
      case "upload":
        // Pass handler down to FileUpload
        return <FileUpload onUploadComplete={handleUploadComplete} />;
      case "simulate":
        // Pass the uploaded data down to SimulationRun
        return <SimulationRun uploadedData={uploadedData} />;
      case "runs":
        return <RunsList />;
      case "chat":
        return <LLMChat />;
      default:
        return <div style={styles.tabContent}>Select a tab above.</div>;
    }
  };

  const getButtonStyle = (tabName) => ({
      ...styles.tabButton, // Base style
      backgroundColor: activeTab === tabName ? 'transparent' : '#f0f0f0',
      borderBottom: activeTab === tabName ? '3px solid #444' : "3px solid transparent",
  });

  return (
    <div style={styles.mainAppContainer}>
      <header style={styles.header}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
        <h1>🚦Traffic Simulation Manager</h1>
        <button
          onClick={onLogout}
          style={{
            padding: "10px 15px",
            backgroundColor: "#dc3545",
            color: "#fff",
            border: "none",
            borderRadius: "5px",
            cursor: "pointer",
            fontSize: "1em",
          }}
        >
          Logout
        </button>
      </div>
      </header>

      <main style={styles.mainContent}>
        <div style={{ display: 'flex', borderBottom: "1px solid #ccc", justifyContent: 'space-between', alignItems: 'center', width: '100%'}}>
          <nav style={styles.nav}>
            <button onClick={() => setActiveTab("upload")} style={getButtonStyle("upload")}>
              Upload Files
            </button>
            <button onClick={() => setActiveTab("simulate")} style={getButtonStyle("simulate")}>
              Run Simulation
            </button>
            <button onClick={() => setActiveTab("runs")} style={getButtonStyle("runs")}>
              View Runs
            </button>
            <button onClick={() => setActiveTab("chat")} style={getButtonStyle("chat")}>
              LLM Chat
            </button>
          </nav>
        </div>
        {renderTab()}
      </main>
      <footer style={styles.footer}>
          <p>&copy; 2025 Simulation Group</p>
      </footer>
    </div>
  );
}


// --- Root App Component (Handles Login State) ---
function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  // const [token, setToken] = useState(null); // Token not actively used after login in this version

  const handleLoginSuccess = useCallback((receivedToken) => {
    setLoggedIn(true);
    // setToken(receivedToken); // Store token if needed for future API calls
    // You might store the token in localStorage/sessionStorage for persistence
    // localStorage.setItem('authToken', receivedToken);
  }, []); // Empty dependency array

   // Check for token in storage on initial load (example)
   /*
   useEffect(() => {
       const storedToken = localStorage.getItem('authToken');
       if (storedToken) {
           // You might want to verify the token with the backend here
           setLoggedIn(true);
           setToken(storedToken);
       }
   }, []);
   */

  return (
    <div>
      {!loggedIn ? (
        <Login onLoginSuccess={handleLoginSuccess} />
      ) : (
        <MainApp 
          onLogout={() => {
            setLoggedIn(false); // Reset login state
            localStorage.removeItem("authToken"); // Optional: Clear token if stored
          }}
        />
        // Add a logout button somewhere in MainApp if needed
        // <button onClick={() => { setLoggedIn(false); setToken(null); localStorage.removeItem('authToken'); }}>Logout</button>
      )}
    </div>
  );
}

// --- Styles (Consider moving to a separate CSS/SCSS file) ---
const styles = {
    mainAppContainer: {
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        fontFamily: 'Arial, sans-serif',
    },
    header: {
        backgroundColor: '#333',
        color: '#fff',
        padding: '15px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap', // Allow wrapping on smaller screens
    },
    nav: {
      display: "flex",
      justifyContent: "center", 
      marginBottom: "15px", // Add spacing below the header
      alignItems: "center", // Ensure proper vertical alignment
    },
    mainContent: {
        flexGrow: 1, // Takes up remaining vertical space
        padding: '20px',
        backgroundColor: '#f9f9f9',
    },
    tabButton: {
      display: "inline-block", // Resembles a tab or link
      padding: "10px 20px", // Adjust padding for a larger clickable area
      border: "none", // Remove any borders
      fontSize: "1.1em", // Slightly larger font for visibility
      transition: "all 0.3s ease", // Smooth hover transition
    },
    footer: {
        backgroundColor: '#333',
        color: '#ccc',
        textAlign: 'center',
        padding: '10px 20px',
        marginTop: 'auto', // Pushes footer to bottom
    },
    formGroup: {
        marginBottom: '20px',
    },
    label: {
        display: 'block',
        marginBottom: '8px',
        fontWeight: 'bold',
        fontSize: '0.95em',
    },
    input: {
        width: '100%',
        padding: '10px',
        border: '1px solid #ccc',
        borderRadius: '4px',
        boxSizing: 'border-box',
        fontSize: '1em',
    },
    fileInfo: {
        fontSize: '0.85em',
        color: '#555',
        marginLeft: '10px',
    },
    button: {
        padding: '12px 20px',
        backgroundColor: '#007BFF',
        color: '#fff',
        border: 'none',
        borderRadius: '5px',
        cursor: 'pointer',
        fontSize: '1em',
        transition: 'opacity 0.3s ease',
        opacity: 1,
        ':disabled': { // Note: Inline styles don't support pseudo-classes directly like this
             opacity: 0.6, // Use JS logic to change style object or use CSS classes
             cursor: 'not-allowed',
        }
    },
     hr: {
         border: 0,
         height: '1px',
         backgroundColor: '#ddd',
         margin: '30px 0',
     },
     resultsArea: {
         marginTop: '25px',
         paddingTop: '20px',
         borderTop: '1px solid #eee',
     },
     statusMessage: {
         fontWeight: 'bold',
         marginBottom: '15px',
         fontSize: '1.1em',
     },
     downloadLink: {
         marginBottom: '20px',
     },
     link: {
        color: '#007BFF',
        textDecoration: 'none',
        fontWeight: 'bold',
        ':hover': { // Note: Inline styles don't support pseudo-classes
             textDecoration: 'underline',
        }
     },
     outputContainer: {
         marginTop: '15px',
     },
     preformattedText: {
         border: '1px solid #ccc',
         padding: '15px',
         maxHeight: '400px', // Increased height
         overflowY: 'auto', // Use 'auto' for scrollbar only when needed
         backgroundColor: '#f5f5f5',
         whiteSpace: 'pre-wrap',
         wordBreak: 'break-word', // Changed from break-all
         fontSize: '0.9em',
         lineHeight: '1.5',
     },
     errorText: {
         backgroundColor: '#ffebee', // Lighter red
         color: '#c62828', // Darker red text
         borderColor: '#e57373', // Reddish border
     },
     list: {
        listStyle: 'none',
        padding: 0,
     },
     listItem: {
        border: '1px solid #eee',
        borderRadius: '5px',
        padding: '15px',
        marginBottom: '10px',
        backgroundColor: '#fff',
     },
     // Chat Styles
     chatBox: {
      display: 'flex', // Enables flexbox layout
      flexDirection: 'column', // Stacks messages vertically
      alignItems: 'flex-start', // Default alignment for LLM messages (left)
      border: '1px solid #ccc',
      borderRadius: '5px',
      padding: '10px',
      height: '350px', // Keeps current height
      overflowY: 'auto',
      marginBottom: '15px',
      backgroundColor: '#fff',
  },     
     userMessage: {
      textAlign: 'right',
      margin: '5px 0', // Keeps spacing between messages
      padding: '8px 12px', // Smaller padding for tighter wrapping
      backgroundColor: '#dcf8c6', // Light green bubble
      borderRadius: '10px', // Keeps the rounded bubble shape
      display: 'inline-block', // Shrinks the width to fit the content tightly
      maxWidth: '70%', // Prevents overly long lines but still fits content
      marginLeft: 'auto', // Pushes the bubble to the right
      wordWrap: 'break-word', // Breaks long words to avoid overflow
    },
     llmMessage: {
         textAlign: 'left',
         margin: '5px 0',
         padding: '8px 12px',
         backgroundColor: '#eee', // Light grey bubble
         borderRadius: '10px',
         maxWidth: '70%',
         marginRight: 'auto', // Push to left
         wordWrap: 'break-word',
     },
     chatForm: {
        display: 'flex',
        gap: '10px',
     },
     chatInput: {
        flexGrow: 1, // Take available space
        padding: '10px',
        border: '1px solid #ccc',
        borderRadius: '5px',
        fontSize: '1em',
     },
     chatButton: {
        padding: '10px 15px',
        backgroundColor: '#007BFF',
        color: '#fff',
        border: 'none',
        borderRadius: '5px',
        cursor: 'pointer',
        fontSize: '1em',
     }
};


export default App;