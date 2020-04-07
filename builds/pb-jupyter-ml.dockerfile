FROM jupyter/minimal-notebook

USER root

# OpenShift allocates the UID for the process, but GID is 0
# Based on an example by Graham Dumpleton
RUN chgrp -R root /home/$NB_USER \
    && find /home/$NB_USER -type d -exec chmod g+rwx,o+rx {} \; \
    && find /home/$NB_USER -type f -exec chmod g+rw {} \; \
    && chgrp -R root /opt/conda \
    && find /opt/conda -type d -exec chmod g+rwx,o+rx {} \; \
    && find /opt/conda -type f -exec chmod g+rw {} \;

RUN ln -s /usr/bin/env /bin/env

ENV HOME /home/$NB_USER

COPY scripts/jupyter/autodownload_and_start.sh /usr/local/bin/autodownload_and_start.sh
RUN chmod a+x /usr/local/bin/autodownload_and_start.sh

RUN echo "graphviz from apt" \
    && apt-get update \
    && apt-get install -y graphviz \
    && apt-get clean

USER $NB_USER

RUN echo "upgrade pip and setuptools" \
    && pip --no-cache-dir install --upgrade pip setuptools

RUN echo "Tensorflow" \
    && pip --no-cache-dir install tensorflow==2.0.0

RUN echo "Scikit-Learn" \
    && pip --no-cache-dir install sklearn

RUN echo "PyTorch and TorchVision" \
    && pip install torch==1.4.0+cpu torchvision==0.5.0+cpu -f https://download.pytorch.org/whl/torch_stable.html

RUN echo "Xgboost" \
    && pip --no-cache-dir install xgboost

RUN echo "Scikit-Image" \
    && pip --no-cache-dir install scikit-image

RUN echo "Graphviz" \
    && pip --no-cache-dir install graphviz

RUN echo "Theano and Keras" \
    && pip --no-cache-dir install Theano \
    && pip --no-cache-dir install PyYAML seaborn keras \
    && true

RUN echo "MNIST image database prepopulation" \
    && mkdir -p ~/.keras/datasets/ \
    && wget https://s3.amazonaws.com/img-datasets/mnist.pkl.gz -O ~/.keras/datasets/mnist.pkl.gz

RUN echo "pydot and pydot-ng" \
    && pip --no-cache-dir install pydot pydot-ng\
    && true

CMD ["/usr/local/bin/autodownload_and_start.sh"]
