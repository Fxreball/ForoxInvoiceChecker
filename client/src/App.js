import React, { useState } from "react";
import "./App.css";

function App() {
  const [dataFacturen, setDataFacturen] = useState([]);
  const [fileFacturen, setFileFacturen] = useState(null);
  const [filePercentages, setFilePercentages] = useState(null);
  const [dataPercentages, setDataPercentages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [controleResultaat, setControleResultaat] = useState([]);
  const [kleurTellingen, setKleurTellingen] = useState({ groen: 0, oranje: 0, rood: 0, control: 0 });

  const handleFileChangeFacturen = (e) => {
    setFileFacturen(e.target.files[0]);
    setControleResultaat([]);
    handleFileUploadFacturen(e.target.files[0]);
  };

  const handleFileChangePercentages = (e) => {
    const file = e.target.files[0];
    if (file.name.split(".")[0] !== "Film percentages") {
      alert("Het percentages bestand moet 'Film percentages' heten.");
      return;
    }
    setError("");
    setFilePercentages(file);
    handleFileUploadPercentages(file);
  };

  const handleFileUploadFacturen = async (file) => {
    if (!file) {
      setError("Kies een bestand om te uploaden.");
      return;
    }

    const formData = new FormData();
    formData.append("bestand", file);
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/upload_factuur", { method: "POST", body: formData });
      if (!response.ok) throw new Error("Fout bij uploaden facturen.");
      const result = await response.json();
      const updatedResult = result.map((factuur) => ({ ...factuur, percentageFilmtitel: "Nog te controleren" }));
      setKleurTellingen({ groen: 0, oranje: 0, rood: 0, control: updatedResult.length });
      setDataFacturen(updatedResult);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUploadPercentages = async (file) => {
    if (!file) {
      setError("Kies een bestand om te uploaden.");
      return;
    }

    const formData = new FormData();
    formData.append("bestand", file);
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/upload_percentages", { method: "POST", body: formData });
      if (!response.ok) throw new Error("Fout bij uploaden percentages.");
      setDataPercentages(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return `${String(date.getDate()).padStart(2, "0")}-${String(date.getMonth() + 1).padStart(2, "0")}-${date.getFullYear()}`;
  };

  const bepaalKleurPercentage = (formPercentage, filmPercentage) => {
    if (formPercentage === "Nog te controleren") return "#FF7F7F";
    if (formPercentage > filmPercentage) return "red";
    if (formPercentage === filmPercentage) return "green";
    if (formPercentage < filmPercentage) return "orange";
    return "#FF7F7F";
  };

  const controleerPercentages = async () => {
    setLoading(true);
    setError("");
    setControleResultaat([]);
    
    let groen = 0, oranje = 0, rood = 0, control = 0;
    
    try {
      const nieuweResultaten = [];
      for (let factuur of dataFacturen) {
        const response = await fetch("/zoek_films", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ master_title_description: factuur.master_title_description, play_week: formatDate(factuur.play_week) }),
        });
  
        if (!response.ok) throw new Error(`Fout: ${await response.text()}`);
        
        const result = await response.json();
        let filmPercentage = "Nog te controleren";
        
        if (result?.[0]?.["Unnamed: 2"] !== undefined) {
          let percentage = result[0]["Unnamed: 2"] * 100;
          filmPercentage = `${percentage.toFixed(2).replace(/\.00$/, "")}%`;
        }
  
        const kleur = filmPercentage === "Nog te controleren" ? "purple" : bepaalKleurPercentage(factuur.frm_perc, parseFloat(filmPercentage));
        
        // Verhoog de control teller wanneer de kleur "Nog te controleren" is
        if (kleur === "purple") control++;
        if (kleur === "green") groen++;
        if (kleur === "orange") oranje++;
        if (kleur === "red") rood++;
  
        nieuweResultaten.push({ ...factuur, percentageFilmtitel: filmPercentage });
      }
  
      setDataFacturen(nieuweResultaten);
      setControleResultaat(nieuweResultaten);
      setKleurTellingen({ groen, oranje, rood, control });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };  

  return (
    <div className="container">
      <div className="input-container">
        <input type="file" onChange={handleFileChangeFacturen} />
        <input type="file" onChange={handleFileChangePercentages} />
      </div>
      <button onClick={controleerPercentages} disabled={loading}>Controleer facturen</button>
      
        {(kleurTellingen.groen > 0 || kleurTellingen.oranje > 0 || kleurTellingen.rood > 0 || kleurTellingen.control > 0) && (
          <div className="kleur-overzicht">
            <>
              <p style={{ color: "green" }}>Goed: {kleurTellingen.groen}</p>
              <p style={{ color: "orange" }}>Te laag: {kleurTellingen.oranje}</p>
              <p style={{ color: "red" }}>Te hoog: {kleurTellingen.rood}</p>
              <p style={{ color: "#FF7F7F" }}>Nog te controleren: {kleurTellingen.control}</p>
            </>
          </div>
        )}
      
      <table>
        <thead>
          <tr><th>Titel</th><th>Speelweek</th><th>Factuur percentage</th><th>Werkelijk percentage</th></tr>
        </thead>
        <tbody>
          {dataFacturen.length > 0 ? dataFacturen.map((item, index) => (
            <tr key={index}>
              <td>{item.master_title_description}</td>
              <td>{formatDate(item.play_week)}</td>
              <td>{item.frm_perc}%</td>
              <td style={{ backgroundColor: bepaalKleurPercentage(item.frm_perc, parseFloat(item.percentageFilmtitel.replace("%", ""))) }}>
                {item.percentageFilmtitel}
              </td>
            </tr>
          )) : <tr><td colSpan="4">Geen facturen beschikbaar.</td></tr>}
        </tbody>
      </table>
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
        </div>
      )}
    </div>
  );
}

export default App;
