import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Slider,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Snackbar
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { getGrowthParameters, updateGrowthParameters } from '../api/financialService';

const ParametersForm = ({ onParametersUpdated }) => {
  const [params, setParams] = useState({
    initial_clients: 100,
    initial_developers: 50,
    initial_affiliates: 20,
    client_growth_rates: [0.08, 0.10, 0.12, 0.15, 0.18],
    developer_growth_rates: [0.05, 0.07, 0.09, 0.11, 0.13],
    affiliate_growth_rates: [0.07, 0.09, 0.12, 0.14, 0.16],
    subscription_price: 20,
    affiliate_commission: 5,
    marketing_percentage: 0.15,
    infrastructure_cost_per_user: 2,
    other_expenses_percentage: 0.10,
    base_salary: 7000,
    salary_increase: 0.05
  });
  
  const [notification, setNotification] = useState({
    open: false,
    message: '',
    severity: 'success'
  });
  
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchParameters = async () => {
      try {
        const data = await getGrowthParameters();
        if (data) {
          setParams(data);
        }
      } catch (error) {
        console.error('Error fetching parameters:', error);
      }
    };
    
    fetchParameters();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setParams((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleGrowthRateChange = (type, index, value) => {
    const newRates = [...params[`${type}_growth_rates`]];
    newRates[index] = value / 100; // Convert from percentage to decimal
    
    setParams((prev) => ({
      ...prev,
      [`${type}_growth_rates`]: newRates
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const result = await updateGrowthParameters(params);
      
      if (result.status === 'success') {
        setNotification({
          open: true,
          message: 'Parameters updated successfully!',
          severity: 'success'
        });
        
        if (onParametersUpdated && result.yearly_summary) {
          onParametersUpdated(result.yearly_summary);
        }
      } else {
        setNotification({
          open: true,
          message: result.message || 'Failed to update parameters',
          severity: 'error'
        });
      }
    } catch (error) {
      console.error('Error updating parameters:', error);
      setNotification({
        open: true,
        message: 'An error occurred while updating parameters',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCloseNotification = () => {
    setNotification((prev) => ({
      ...prev,
      open: false
    }));
  };

  return (
    <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h5" gutterBottom>
        Adjust Growth Parameters
      </Typography>
      
      <form onSubmit={handleSubmit}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Initial Values
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Initial Clients"
                name="initial_clients"
                type="number"
                value={params.initial_clients}
                onChange={handleChange}
                fullWidth
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Initial Developers"
                name="initial_developers"
                type="number"
                value={params.initial_developers}
                onChange={handleChange}
                fullWidth
                variant="outlined"
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                label="Initial Affiliates"
                name="initial_affiliates"
                type="number"
                value={params.initial_affiliates}
                onChange={handleChange}
                fullWidth
                variant="outlined"
                size="small"
              />
            </Grid>
          </Grid>
        </Box>
        
        <Divider sx={{ my: 2 }} />
        
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Monthly Growth Rates</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={3}>
              {['client', 'developer', 'affiliate'].map((type) => (
                <Grid item xs={12} key={type}>
                  <Typography variant="subtitle1" gutterBottom>
                    {type.charAt(0).toUpperCase() + type.slice(1)} Growth Rates (% per month)
                  </Typography>
                  <Grid container spacing={2}>
                    {params[`${type}_growth_rates`].map((rate, index) => (
                      <Grid item xs={12} sm={2.4} key={`${type}-${index}`}>
                        <Typography>Year {index + 1}</Typography>
                        <Slider
                          value={rate * 100}
                          onChange={(e, newValue) => handleGrowthRateChange(type, index, newValue)}
                          aria-labelledby={`${type}-year-${index+1}-slider`}
                          valueLabelDisplay="auto"
                          step={0.5}
                          min={0}
                          max={30}
                          valueLabelFormat={(value) => `${value}%`}
                        />
                        <Typography variant="caption" sx={{ display: 'block', textAlign: 'center' }}>
                          {(rate * 100).toFixed(1)}%
                        </Typography>
                      </Grid>
                    ))}
                  </Grid>
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>
        
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Pricing & Cost Parameters</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Subscription Price ($)"
                  name="subscription_price"
                  type="number"
                  value={params.subscription_price}
                  onChange={handleChange}
                  fullWidth
                  variant="outlined"
                  size="small"
                  InputProps={{ inputProps: { min: 0, step: 0.01 } }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Affiliate Commission ($)"
                  name="affiliate_commission"
                  type="number"
                  value={params.affiliate_commission}
                  onChange={handleChange}
                  fullWidth
                  variant="outlined"
                  size="small"
                  InputProps={{ inputProps: { min: 0, step: 0.01 } }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Marketing (% of Revenue)"
                  name="marketing_percentage"
                  type="number"
                  value={params.marketing_percentage * 100}
                  onChange={(e) => handleChange({
                    target: {
                      name: 'marketing_percentage',
                      value: parseFloat(e.target.value) / 100
                    }
                  })}
                  fullWidth
                  variant="outlined"
                  size="small"
                  InputProps={{ inputProps: { min: 0, max: 100, step: 0.1 } }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Other Expenses (% of Revenue)"
                  name="other_expenses_percentage"
                  type="number"
                  value={params.other_expenses_percentage * 100}
                  onChange={(e) => handleChange({
                    target: {
                      name: 'other_expenses_percentage',
                      value: parseFloat(e.target.value) / 100
                    }
                  })}
                  fullWidth
                  variant="outlined"
                  size="small"
                  InputProps={{ inputProps: { min: 0, max: 100, step: 0.1 } }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Infrastructure Cost per User ($)"
                  name="infrastructure_cost_per_user"
                  type="number"
                  value={params.infrastructure_cost_per_user}
                  onChange={handleChange}
                  fullWidth
                  variant="outlined"
                  size="small"
                  InputProps={{ inputProps: { min: 0, step: 0.01 } }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Base Salary ($)"
                  name="base_salary"
                  type="number"
                  value={params.base_salary}
                  onChange={handleChange}
                  fullWidth
                  variant="outlined"
                  size="small"
                  InputProps={{ inputProps: { min: 0 } }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Annual Salary Increase (%)"
                  name="salary_increase"
                  type="number"
                  value={params.salary_increase * 100}
                  onChange={(e) => handleChange({
                    target: {
                      name: 'salary_increase',
                      value: parseFloat(e.target.value) / 100
                    }
                  })}
                  fullWidth
                  variant="outlined"
                  size="small"
                  InputProps={{ inputProps: { min: 0, max: 100, step: 0.1 } }}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
        
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button 
            type="submit" 
            variant="contained" 
            color="primary" 
            size="large"
            disabled={loading}
          >
            {loading ? 'Updating...' : 'Update Forecast'}
          </Button>
        </Box>
      </form>
      
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseNotification} severity={notification.severity}>
          {notification.message}
        </Alert>
      </Snackbar>
    </Paper>
  );
};

export default ParametersForm;
