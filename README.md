# Data-Sensing-and-TinyML-for-Edge-Processing
Data Sensing and TinyML for Edge Processing

My internship project primarily focused on TinyML for edge processing. I developed and tested various models using a dataset provided by my mentor, and then converted them into space-optimized, low-cost versions suitable for deployment on Microcontroller Units (MCUs) such as the ESP32. These models generate predictions for specific water parameters, determining potability and identifying anomalies in water quality patterns over a 24-hour period.

While the true essence of TinyML lies in deploying models directly on MCUs, due to time constraints and limited hardware availability, I conducted latency testing using Google Cloud Platform (GCP). Additionally, I built a basic web dashboard linked to GCP and Firebase Realtime Database for visualizing predictions and system behavior. The complete code has also been included in the repository.

Though I was unable to deploy the models on actual hardware, I had thoroughly researched the steps one would take in order to test the models on a MCU prototype, which I have listed as follws:
1. Train and convert the model: convert the model using .tflite and save the files. (I have added the tflite files wherever necessary through out the repo)
2. Apply full integer Quantization: improves performance on MCU. (Already done)
3. Convert to C array: Use xxd to convert the model into a C header file:
   ```bash
   xxd -i model.tflite > model.h
   ```
   This creates a byte array (g_model) that can be embedded in firmware.
4. Set Up Your MCU Project: Install the TensorFlow Lite for Microcontrollers library (available via Arduino Library Manager or PlatformIO). Include the generated model.h in your project. Set up the TensorFlow Lite interpreter:
   ```cpp
   #include "model.h"
   #include "tensorflow/lite/micro/micro_interpreter.h"
   #include "tensorflow/lite/micro/all_ops_resolver.h"
   #include "tensorflow/lite/schema/schema_generated.h"

   const tflite::Model* model = tflite::GetModel(g_model);
   tflite::MicroInterpreter interpreter(model, resolver, tensor_arena, tensor_arena_size, &error_reporter);
     interpreter.AllocateTensors();
   ```
5. Run Inference:
   ```cpp
   TfLiteTensor* input = interpreter.input(0);
   input->data.f[0] = your_input_value;
   
   interpreter.Invoke();

   TfLiteTensor* output = interpreter.output(0);
   float result = output->data.f[0];
   ```

Further I have also documented the methods of using GCP and the Firebase Realtime Database:
1. Create an account in GCP: For this step you will require a payment method and must pay Rs. 2 intitally for verfication which was later returned. Do note thatt this is not a free resource. There will be some free credits initially which one can use but after long usage it will incur charges.
2. Go to Vertex AI and create a Colab notebook: Here you can retrain the model and also save the .tflite file for further simulation
3. Create GCP Buckets for simualting the models: This way you can access the model for inference
4. Create a Realtime Database in Firebase: They will provide a config for the database which needs to be used later in the web-dashboard for displaying the anomalies
   ```script
   const firebaseConfig = {
   apiKey: "AIzaSyC3HlGFTk8W_kv9rRLgqviRc1HBeW99ZXc",
   authDomain: "hale-lab-7a638.firebaseapp.com",
   databaseURL: "https://hale-lab-7a638-default-rtdb.firebaseio.com",
   projectId: "hale-lab-7a638",
   storageBucket: "hale-lab-7a638.firebasestorage.app",
   messagingSenderId: "512965882466",
   appId: "1:512965882466:web:c9a2ca7a6a690ff2c0973b",
   measurementId: "G-1YBGYFY3DN"
   };
   ```
   This is a sample config which is deprecated from one of my previous tests.
5. Run inference code: This will simulate the way of how data would be recieved from the sensors and sent to the model

---

Overall this was a very fruitful and engaging experience for me as I learnt a lot about TinyML and how it's significance is increasing day by day. For any other details kindly refer to my Internship Report which is also added in this repo.

   
   
